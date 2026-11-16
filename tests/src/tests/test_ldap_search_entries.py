from .features import LdapTestCase, ROOT_DC


class TestLdapRemoveEntries(LdapTestCase):
    def test_search_all_in_root_dc(self):

        def search_all_in_root_dc(con, context, data):
            return (
                con.search('' + ROOT_DC, '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertTrue, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertFalse, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_all_in_root_dc,
            test_suite,
            "testing to search in root dc"
        )

    def test_search_all_users(self):

        def search_all_people(con, context, data):
            return (
                con.search('ou=people,' + ROOT_DC, '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertFalse, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertTrue, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_all_people,
            test_suite,
            "testing to search all people"
        )

    def test_search_all_groups(self):

        def search_all_groups(con, context, data):
            return (
                con.search('ou=groups,' + ROOT_DC, '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertFalse, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertTrue, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_all_groups,
            test_suite,
            "testing to search all groups"
        )

    def test_search_all_applications(self):

        def search_all_apps(con, context, data):
            return (
                con.search('ou=applications,' + ROOT_DC, '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertFalse, },
            'user-apps-admin': {'assert': self.assertTrue, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertFalse, },
            'app-people-admin': {'assert': self.assertFalse, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_all_apps,
            test_suite,
            "testing to search all apps"
        )

    def test_search_all_policies(self):

        def search_all_policies(con, context, data):
            return (
                con.search('ou=policies,' + ROOT_DC, '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertFalse, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertFalse, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertFalse, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_all_policies,
            test_suite,
            "testing to search all policies"
        )

    def test_search_own_entry(self):

        def search_myself(con, context, data):
            return (
                con.search(context['user_dn'], '(objectclass=*)'),
                con.result
            )

        test_suite = {
            'anonymous': None,
            'user': {'assert': self.assertTrue, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertTrue, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': None,
            'app': {'assert': self.assertTrue, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_myself,
            test_suite,
            "testing to search myself"
        )

    def test_search_member_of(self):

        def search_member_of(con, context, data):
            return (
                con.search(
                    'ou=people,' + ROOT_DC,
                    '(& (objectclass=inetOrgPerson)'
                    '   (memberOf=cn=fakeapp,ou=groups,' + ROOT_DC + '))'
                ),
                con.result
            )

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {'assert': self.assertTrue, },
            'user-apps-admin': {'assert': self.assertFalse, },
            'user-admin': {'assert': self.assertTrue, },
            'admin': {'assert': self.assertTrue, },
            'app': {'assert': self.assertTrue, },
            'app-people-admin': {'assert': self.assertTrue, },
            'app-apps-admin': {'assert': self.assertTrue, },
            'app-admin': {'assert': self.assertTrue, },
        }

        self.run_case(
            search_member_of,
            test_suite,
            "testing to search people member of fakeapp"
        )

    def test_app_cannot_read_restricted_people_attributes(self):
        from uuid import uuid4
        user_uid = "user-%s" % uuid4()
        user_dn = "uid=%s,ou=people,%s" % (user_uid, ROOT_DC)
        self.create_user(user_uid, user_dn)

        def cleanup():
            from .features import ldap_connection, ROOT_LDAP_DN, ROOT_LDAP_SECRET
            with ldap_connection(
                    dn=ROOT_LDAP_DN, password=ROOT_LDAP_SECRET
            ) as root_con:
                root_con.delete(user_dn)

        self.addCleanup(cleanup)

        def search_user_attrs(con, context, data):
            res = con.search(
                user_dn,
                '(objectclass=inetOrgPerson)',
                attributes=['uid', 'cn', 'mobile']
            )
            if res and con.entries:
                entry = con.entries[0]
                data['has_uid'] = bool(entry.uid.values)
                data['has_mobile'] = bool(entry.mobile.values)
            else:
                data['has_uid'] = False
                data['has_mobile'] = False
            return res, con.result

        def assert_only_identity_attrs(con, context, data):
            self.assertTrue(data.get('has_uid'))
            self.assertFalse(data.get('has_mobile'))

        def assert_all_attrs(con, context, data):
            self.assertTrue(data.get('has_uid'))
            self.assertTrue(data.get('has_mobile'))

        test_suite = {
            'anonymous': {'assert': self.assertFalse, },
            'user': {'assert': self.assertFalse, },
            'user-people-admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_all_attrs,
            },
            'user-apps-admin': {'assert': self.assertFalse, },
            'user-admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_all_attrs,
            },
            'admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_all_attrs,
            },
            'app': {
                'assert': self.assertTrue,
                'run_after_test': assert_only_identity_attrs,
            },
            'app-people-admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_all_attrs,
            },
            'app-apps-admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_only_identity_attrs,
            },
            'app-admin': {
                'assert': self.assertTrue,
                'run_after_test': assert_all_attrs,
            },
        }

        self.run_case(
            search_user_attrs,
            test_suite,
            "testing that apps can only read basic identity attributes on people"
        )
