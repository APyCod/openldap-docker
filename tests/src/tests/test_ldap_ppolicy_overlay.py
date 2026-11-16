from uuid import uuid4
from ldap3 import MODIFY_REPLACE

from .features import (
    LdapTestCase, ldap_connection, ROOT_LDAP_DN, ROOT_DC, ROOT_LDAP_SECRET
)


class TestLdapPPolicyOverlay(LdapTestCase):

    def test_update_own_pwdPolicySubentry(self):

        def prepare_test(con, context, data):
            policy_cn = "policy-%s" % uuid4()
            policy_dn = "cn=%s,ou=policies,%s" % (policy_cn, ROOT_DC)
            self.create_policy(policy_cn, policy_dn)
            data["dn"] = policy_dn

        def update_pwdsubpolicy_attribute(con, context, data):
            return (
                con.modify(
                    context['user_dn'],
                    {'pwdPolicySubentry': [(MODIFY_REPLACE, data['dn'])]}),
                con.result
            )

        def assert_pwdsubpolicy_changed(con, context, data):
            with ldap_connection(
                    dn=ROOT_LDAP_DN, password=ROOT_LDAP_SECRET
            ) as root_con:
                root_con.search(
                    context['user_dn'],
                    '(objectclass=inetOrgPerson)',
                    attributes=['pwdPolicySubentry']
                )
                self.assertEqual(
                    data['dn'],
                    root_con.entries[0].pwdPolicySubentry.value
                )

        def assert_pwdsubpolicy_not_changed(con, context, data):
            with ldap_connection(
                    dn=ROOT_LDAP_DN, password=ROOT_LDAP_SECRET
            ) as root_con:
                root_con.search(
                    context['user_dn'],
                    '(objectclass=inetOrgPerson)',
                    attributes=['pwdPolicySubentry']
                )
                self.assertNotEqual(
                    data['dn'],
                    root_con.entries[0].pwdPolicySubentry.value,
                    "user %s - pwdsubpolicy shouldn't been changed" % (
                        context['user_dn'],
                    )
                )

        test_suite = {
            'anonymous': None,
            'user': {
                'assert': self.assertFalse,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_not_changed
            },
            'user-people-admin': {
                'assert': self.assertTrue,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_changed
            },
            'user-apps-admin': {
                'assert': self.assertFalse,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_not_changed
            },
            'user-admin': {
                'assert': self.assertTrue,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_changed
            },
            'admin': None,
            'app': {
                'assert': self.assertFalse,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_not_changed
            },
            'app-people-admin': {
                'assert': self.assertFalse,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_not_changed
            },
            'app-apps-admin': {
                'assert': self.assertTrue,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_changed
            },
            'app-admin': {
                'assert': self.assertTrue,
                'run_before_test': prepare_test,
                'run_after_test': assert_pwdsubpolicy_changed
            },
        }
        self.run_case(
            update_pwdsubpolicy_attribute,
            test_suite,
            "testing to update its own cn attribute"
        )

    def test_default_policy_min_length_and_admin_reset(self):
        user_uid = "user-%s" % uuid4()
        user_dn = "uid=%s,ou=people,%s" % (user_uid, ROOT_DC)
        initial_pass = "InitialStrongPass-%s" % uuid4()

        def clean():
            with ldap_connection(
                    dn=ROOT_LDAP_DN, password=ROOT_LDAP_SECRET
            ) as root_con:
                root_con.delete(user_dn)

        self.addCleanup(clean)
        self.create_user(user_uid, user_dn)
        self.reset_password(user_dn, initial_pass)

        with ldap_connection(dn=user_dn, password=initial_pass) as user_con:
            # pwdMinLength: 12 must reject a short password
            ok, _ = self.change_ldap_password(
                user_con, user_dn, initial_pass, "short123"
            )
            self.assertFalse(ok, "Password shorter than 12 chars should fail")

            # Valid >= 12-char password with old password must succeed
            new_pass = "NewStrongPass-%s" % uuid4()
            ok, res = self.change_ldap_password(
                user_con, user_dn, initial_pass, new_pass
            )
            self.assertTrue(ok, res)

        # Non-root ldap_people_admin (user & app, e.g. Authelia) must be able
        # to reset a user's password under the default policy without knowing
        # the old password (pwdSafeModify: FALSE by default).
        for admin_role in ('app-people-admin', 'user-people-admin'):
            admin_ctx = self.users[admin_role]
            reset_pass = "AdminResetPass-%s" % uuid4()
            with ldap_connection(
                dn=admin_ctx['user_dn'], password=admin_ctx['password']
            ) as admin_con:
                self.assertTrue(
                    admin_con.modify(
                        user_dn,
                        {'userPassword': [(MODIFY_REPLACE, [reset_pass])]}
                    ),
                    "Role %s failed to reset password: %r" % (
                        admin_role, admin_con.result
                    )
                )
            with ldap_connection(dn=user_dn, password=reset_pass) as user_con:
                self.assertTrue(
                    user_con.search(user_dn, '(objectclass=*)'),
                    user_con.result
                )
