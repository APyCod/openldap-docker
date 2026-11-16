#!/bin/bash

# Exist in case of error
set -e

# Display running commands
set -x

DATETIME=`date "+%Y%m%d_%H%M%S"`
TEST_LDAP_CT="CI_test_ldap"
CURRENT_BUILD_LDAP_TAG=${CURRENT_BUILD_LDAP_TAG:-"build_$DATETIME"}
CURRENT_BUILD_TEST_LDAP_TAG=${CURRENT_BUILD_TEST_LDAP_TAG:-"build_$DATETIME"}
CURRENT_BUILD_LDAP_TAG="latest"
CURRENT_BUILD_TEST_LDAP_TAG="latest"
SELF_CA_IMAGE="self-certif"
SELF_CA_IMAGE_TAG=latest
CURRENT_DIR=`pwd`
KEEP_RUNNING=${KEEP_RUNNING:-false}
LDAP_PORTS=${LDAP_PORTS:-"-p 636:636"}
CERTIFICAT_VOLUME_NAME="CI_ldap_certificat"
DOMAIN="ci.example.org"
SUB_DOMAIN="ldap"
LDAP_HOST="$SUB_DOMAIN.$DOMAIN"
LDAP_IMAGE=${LDAP_IMAGE:-"$LDAP_HOST"}
LDAP_CT="CI_ldap"
TEST_LDAP_IMAGE="test_ldap"
LDAP_NETWORK=net_ci_ldap
LDAP_NETWORK_MASK=144.18.0.0/16
LDAP_SERVER_IP=144.18.0.23
DOCKER_TTY=""
if [ -t 0 ]; then
    DOCKER_TTY="-it"
fi

USAGE="Usage: $0 [-h] [-k]

Script to test and validate ldap.example.com image
before deploy it on production.

Options:
    -h           Show this help.
    -k           Keep ldap running and map 636 port
"


while getopts "hk" OPTION
do
    case $OPTION in
        h) echo "$USAGE";
           exit;;
        k) KEEP_RUNNING=true;;
        *) echo "Unknown parameter... ";
           echo "$USAGE";
           exit 1;;
    esac
done


function cleanup_env {
    set +e
    docker rm -v -f $TEST_LDAP_CT
    docker rm -v -f $LDAP_CT
    docker rm -v -f CI_ldap_migration
    docker volume rm $CERTIFICAT_VOLUME_NAME
    docker volume rm CI_ldap_data
    docker network rm $LDAP_NETWORK
    set -e
}

function build_ldap_image {
    docker build -t $LDAP_IMAGE:$CURRENT_BUILD_LDAP_TAG .
}

function build_test_ldap_image {
    docker build \
        -t $TEST_LDAP_IMAGE:$CURRENT_BUILD_TEST_LDAP_TAG \
        -f tests/Dockerfile \
        ./tests/
}

function prepare_certificates {
    # TODO: split as other build time and use to easly maintains
    # if we move some image outside
    docker volume create $CERTIFICAT_VOLUME_NAME
    docker build \
        -t $SELF_CA_IMAGE:$SELF_CA_IMAGE_TAG \
        -f tests/certificate/Dockerfile \
        ./tests/certificate/
    docker run \
        $DOCKER_TTY --rm \
        -v $CERTIFICAT_VOLUME_NAME:/certificate \
        -e UID=666 \
        -e GID=666 \
        -e CA_DOMAIN=$DOMAIN \
        -e CERT_SUB_DOMAIN=$SUB_DOMAIN \
        $SELF_CA_IMAGE:$SELF_CA_IMAGE_TAG
}

function run_ldap {
    docker network create --subnet=$LDAP_NETWORK_MASK  $LDAP_NETWORK
    PORTS=""
    if $KEEP_RUNNING; then
        PORTS=$LDAP_PORTS
    fi
    docker run -d \
        --network $LDAP_NETWORK \
        --ip $LDAP_SERVER_IP \
        -v $CURRENT_DIR/init/:/srv/ldap/init \
        -v $CURRENT_DIR/demo:/srv/ldap/demo \
        -v $CERTIFICAT_VOLUME_NAME:/ssl \
        -e LDAP_CA_CERTIFICATE_PATH="/ssl/ca.crt" \
        -e LDAP_ROOT_PASSWORD="{SSHA}vvcG8bTEFKggJ8J2wRu/JN9x/4jhRuZF" \
        -e LDAP_DEFAULT_ADMIN_UID="test_default_admin" \
        -e LDAP_DEFAULT_ADMIN_PASSWORD="{SSHA}dPnmfOhPSY3QrdJ73YH9gQM4Ws2vhuDx" \
        -e LDAP_CERTIFICATE_PATH="/ssl/$LDAP_HOST.crt" \
        -e LDAP_CERTIFICATE_KEY_PATH="/ssl/$LDAP_HOST.key" \
        -e DOMAIN="$DOMAIN" \
        -e LDAP_SUB_DOMAIN="$SUB_DOMAIN" \
        $PORTS \
        --name $LDAP_CT $LDAP_IMAGE:$CURRENT_BUILD_LDAP_TAG

    # Make sure ldap is ready
    sleep 2
    # Make sure ldap is running
    if [[ `docker inspect -f {{.State.Running}} $LDAP_CT` != "true" ]]; then
        docker logs $LDAP_CT
        echo "Ldap server is not running, something goes wrong,
              read above Docker container $LDAP_CT logs"
        exit 1
    fi
}

function run_tests {
    docker run \
        --network $LDAP_NETWORK \
        --add-host $LDAP_HOST:$LDAP_SERVER_IP \
        -e LDAP_HOST="ldaps://$LDAP_HOST" \
        -e ROOT_DC="dc=$(echo "$DOMAIN" | sed -e 's/\./,dc=/g')" \
        -v $CERTIFICAT_VOLUME_NAME:/ssl \
        $DOCKER_TTY --rm \
        $TEST_LDAP_IMAGE:$CURRENT_BUILD_TEST_LDAP_TAG
}

function stop_ldap {
    docker stop $LDAP_CT
    docker network rm $LDAP_NETWORK
}

function test_persistence_and_migration {
    DATA_VOL="CI_ldap_data"
    MIG_CT="CI_ldap_migration"
    docker volume create "$DATA_VOL"

    # 1. Initial start with persistent /var/lib/openldap and ephemeral slapd.d
    docker run -d \
        -v "$DATA_VOL":/var/lib/openldap \
        -v "$CERTIFICAT_VOLUME_NAME":/ssl \
        -e LDAP_CA_CERTIFICATE_PATH="/ssl/ca.crt" \
        -e LDAP_CERTIFICATE_PATH="/ssl/$LDAP_HOST.crt" \
        -e LDAP_CERTIFICATE_KEY_PATH="/ssl/$LDAP_HOST.key" \
        -e DOMAIN="$DOMAIN" \
        -e LDAP_SUB_DOMAIN="$SUB_DOMAIN" \
        --name "$MIG_CT" "$LDAP_IMAGE:$CURRENT_BUILD_LDAP_TAG"
    sleep 2
    if [[ `docker inspect -f {{.State.Running}} "$MIG_CT"` != "true" ]]; then
        docker logs "$MIG_CT"
        exit 1
    fi
    docker exec "$MIG_CT" test -f /var/lib/openldap/.migration_version
    docker exec "$MIG_CT" test -f /var/lib/openldap/.image_version
    docker rm -f "$MIG_CT"

    # 2. Simulate pre-versioning volume (remove version markers) and restart
    docker run --rm \
        -v "$DATA_VOL":/var/lib/openldap \
        --entrypoint sh "$LDAP_IMAGE:$CURRENT_BUILD_LDAP_TAG" \
        -c "rm -f /var/lib/openldap/.migration_version /var/lib/openldap/.image_version"

    docker run -d \
        -v "$DATA_VOL":/var/lib/openldap \
        -v "$CERTIFICAT_VOLUME_NAME":/ssl \
        -e LDAP_CA_CERTIFICATE_PATH="/ssl/ca.crt" \
        -e LDAP_CERTIFICATE_PATH="/ssl/$LDAP_HOST.crt" \
        -e LDAP_CERTIFICATE_KEY_PATH="/ssl/$LDAP_HOST.key" \
        -e DOMAIN="$DOMAIN" \
        -e LDAP_SUB_DOMAIN="$SUB_DOMAIN" \
        --name "$MIG_CT" "$LDAP_IMAGE:$CURRENT_BUILD_LDAP_TAG"
    sleep 2
    if [[ `docker inspect -f {{.State.Running}} "$MIG_CT"` != "true" ]]; then
        docker logs "$MIG_CT"
        exit 1
    fi
    docker logs "$MIG_CT" | grep -q "Applying migration 1"
    docker exec "$MIG_CT" test -f /var/lib/openldap/.migration_version
    docker rm -f "$MIG_CT"
    docker volume rm "$DATA_VOL"
}

cleanup_env
build_ldap_image
build_test_ldap_image
prepare_certificates
run_ldap
run_tests
if ! $KEEP_RUNNING; then
    stop_ldap
    test_persistence_and_migration
fi
