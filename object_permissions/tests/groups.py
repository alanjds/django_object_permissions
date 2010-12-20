from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from django.test.client import Client

from object_permissions import *
from object_permissions.registration import TestModel, UnknownPermissionException

__all__ = ('TestGroups','TestGroupViews')


class TestGroups(TestCase):
    perms = [u'Perm1', u'Perm2', u'Perm3', u'Perm4']
    
    def setUp(self):
        self.tearDown()
        
        User(id=1, username='anonymous').save()
        settings.ANONYMOUS_USER_ID=1
        
        user0 = User(id=2, username='tester0')
        user0.set_password('secret')
        user0.save()
        user1 = User(id=3, username='tester1')
        user1.set_password('secret')
        user1.save()
        
        object0 = TestModel.objects.create(name='test0')
        object0.save()
        object1 = TestModel.objects.create(name='test1')
        object1.save()
        
        dict_ = globals()
        dict_['user0']=user0
        dict_['user1']=user1
        dict_['object0']=object0
        dict_['object1']=object1
        dict_['perms']=self.perms
    
    def tearDown(self):
        User.objects.all().delete()
        TestModel.objects.all().delete()
        Group.objects.all().delete()

    def test_trivial(self):
        """ Test instantiating a Group """
        group = Group()

    def test_save(self, name='test', user=None):
        """ Test saving an Group """
        group = Group(name=name)
        group.save()
        
        if user:
            group.user_set.add(user)
        
        return group
    
    def test_permissions(self):
        """ Verify all model perms are created """
        self.assertEqual(['admin'], get_model_perms(Group))
    
    def test_grant_group_permissions(self):
        """
        Test granting permissions to a Group
       
        Verifies:
            * granted properties are available via backend (has_perm)
            * granted properties are only granted to the specified user, object
              combinations
            * granting unknown permission raises error
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        # grant single property
        group0.grant('Perm1', object0)
        self.assert_(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', object1))
        self.assertFalse(user1.has_perm('Perm1', object0))
        self.assertFalse(user1.has_perm('Perm1', object1))
        
        # grant property again
        group0.grant('Perm1', object0)
        self.assert_(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', object1))
        self.assertFalse(user1.has_perm('Perm1', object0))
        self.assertFalse(user1.has_perm('Perm1', object1))
        
        # grant second property
        group0.grant('Perm2', object0)
        self.assert_(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', object1))
        self.assertFalse(user1.has_perm('Perm1', object0))
        self.assertFalse(user1.has_perm('Perm1', object1))
        self.assert_(user0.has_perm('Perm2', object0))
        self.assertFalse(user0.has_perm('Perm2', object1))
        self.assertFalse(user1.has_perm('Perm2', object0))
        self.assertFalse(user1.has_perm('Perm2', object1))
        
        # grant property to another object
        group0.grant('Perm2', object1)
        self.assert_(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', object1))
        self.assertFalse(user1.has_perm('Perm1', object0))
        self.assertFalse(user1.has_perm('Perm1', object1))
        self.assert_(user0.has_perm('Perm2', object0))
        self.assert_(user0.has_perm('Perm2', object1))
        self.assertFalse(user1.has_perm('Perm2', object0))
        self.assertFalse(user1.has_perm('Perm2', object1))
        
        # grant perms to other user
        group1.grant('Perm3', object0)
        self.assert_(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', object1))
        self.assertFalse(user1.has_perm('Perm1', object0))
        self.assertFalse(user1.has_perm('Perm1', object1))
        self.assert_(user0.has_perm('Perm2', object0))
        self.assert_(user0.has_perm('Perm2', object1))
        self.assertFalse(user1.has_perm('Perm2', object0))
        self.assertFalse(user1.has_perm('Perm2', object1))
        self.assert_(user1.has_perm('Perm3', object0))
        
        def grant_unknown():
            group1.grant('UnknownPerm', object0)
        self.assertRaises(UnknownPermissionException, grant_unknown)
    
    def test_revoke_group_permissions(self):
        """
        Test revoking permissions from Groups
        
        Verifies:
            * revoked properties are removed
            * revoked properties are only removed from the correct Group/obj combinations
            * revoking property Group does not have does not give an error
            * revoking unknown permission raises error
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        # revoke perm when user has no perms
        revoke(group0, 'Perm1', object0)
        
        for perm in perms:
            group0.grant(perm, object0)
            group0.grant(perm, object1)
            group1.grant(perm, object0)
            group1.grant(perm, object1)
        
        # revoke single perm
        group0.revoke('Perm1', object0)
        self.assertEqual([u'Perm2', u'Perm3', u'Perm4'], group0.get_perms(object0))
        self.assertEqual(perms, group0.get_perms(object1))
        self.assertEqual(perms, group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
        
        # revoke a second perm
        group0.revoke('Perm3', object0)
        self.assertEqual([u'Perm2', u'Perm4'], group0.get_perms(object0))
        self.assertEqual(perms, group0.get_perms(object1))
        self.assertEqual(perms, group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
        
        # revoke from another object
        group0.revoke('Perm3', object1)
        self.assertEqual([u'Perm2', u'Perm4'], group0.get_perms(object0))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm4'], group0.get_perms(object1))
        self.assertEqual(perms, group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
        
        # revoke from another user
        group1.revoke('Perm4', object0)
        self.assertEqual([u'Perm2', u'Perm4'], group0.get_perms(object0))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm4'], group0.get_perms(object1))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm3'], group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
        
        # revoke perm user does not have
        group0.revoke('Perm1', object0)
        self.assertEqual([u'Perm2', u'Perm4'], group0.get_perms(object0))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm4'], group0.get_perms(object1))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm3'], group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
        
        # revoke perm that does not exist
        group0.revoke('DoesNotExist', object0)
        self.assertEqual([u'Perm2', u'Perm4'], group0.get_perms(object0))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm4'], group0.get_perms(object1))
        self.assertEqual([u'Perm1', u'Perm2', u'Perm3'], group1.get_perms(object0))
        self.assertEqual(perms, group1.get_perms(object1))
    
    def test_revoke_all_group(self):
        """
        Test revoking all permissions from a group
        
        Verifies
            * revoked properties are only removed from the correct user/obj combinations
            * revoking property user does not have does not give an error
            * revoking unknown permission raises error
        """
        group0 = self.test_save('TestGroup0')
        group1 = self.test_save('TestGroup1')
        
        for perm in perms:
            grant_group(group0, perm, object0)
            grant_group(group0, perm, object1)
            grant_group(group1, perm, object0)
            grant_group(group1, perm, object1)
        
        revoke_all_group(group0, object0)
        self.assertEqual([], get_group_perms(group0, object0))
        self.assertEqual(perms, get_group_perms(group0, object1))
        self.assertEqual(perms, get_group_perms(group1, object0))
        self.assertEqual(perms, get_group_perms(group1, object1))
        
        revoke_all_group(group0, object1)
        self.assertEqual([], get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual(perms, get_group_perms(group1, object0))
        self.assertEqual(perms, get_group_perms(group1, object1))
        
        revoke_all_group(group1, object0)
        self.assertEqual([], get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        self.assertEqual(perms, get_group_perms(group1, object1))
        
        revoke_all_group(group1, object1)
        self.assertEqual([], get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        self.assertEqual([], get_group_perms(group1, object1))
    
    def test_set_perms(self):
        """
        Test setting perms to an exact set
        """
        group0 = self.test_save('TestGroup0')
        group1 = self.test_save('TestGroup1')
        perms1 = self.perms
        perms2 = ['Perm1', 'Perm2']
        perms3 = ['Perm2', 'Perm3']
        perms4 = []
        
        # grant single property
        set_group_perms(group0, perms1, object0)
        self.assertEqual(perms1, get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        
        set_group_perms(group0, perms2, object0)
        self.assertEqual(perms2, get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        
        set_group_perms(group0, perms3, object0)
        self.assertEqual(perms3, get_group_perms(group0, object0))
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        
        # remove perms
        set_group_perms(group0, perms4, object0)
        self.assertEqual(perms4, get_group_perms(group0, object0))
        self.assertFalse(group0.TestModel_gperms.filter(obj=object0).exists())
        self.assertEqual([], get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        
        set_group_perms(group0, perms2, object1)
        self.assertEqual(perms4, get_group_perms(group0, object0))
        self.assertEqual(perms2, get_group_perms(group0, object1))
        self.assertEqual([], get_group_perms(group1, object0))
        
        set_group_perms(group1, perms1, object0)
        self.assertEqual(perms4, get_group_perms(group0, object0))
        self.assertEqual(perms2, get_group_perms(group0, object1))
        self.assertEqual(perms1, get_group_perms(group1, object0))
    
    def test_has_perm(self):
        """
        Additional tests for has_perms
        
        Verifies:
            * None object always returns false
            * Nonexistent perm returns false
            * Perm user does not possess returns false
        """
        group = self.test_save('TestGroup0', user0)
        group.grant('Perm1', object0)
        
        self.assertTrue(user0.has_perm('Perm1', object0))
        self.assertFalse(user0.has_perm('Perm1', None))
        self.assertFalse(user0.has_perm('DoesNotExist', object0))
        self.assertFalse(user0.has_perm('Perm2', object0))
    
    def test_group_has_perm(self):
        """
        Test Group.has_perm
        
        Verifies:
            * None object always returns false
            * Nonexistent perm returns false
            * Perm user does not possess returns false
        """
        group = self.test_save('TestGroup0', user0)
        group.grant('Perm1', object0)
        
        self.assertTrue(group.has_perm('Perm1', object0))
        self.assertFalse(group.has_perm('Perm1', None))
        self.assertFalse(group.has_perm('DoesNotExist', object0))
        self.assertFalse(group.has_perm('Perm2', object0))
    
    def test_group_has_any_perm(self):
        """
        Test group_has_any_perms.  Group having any of the listed perms
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user0)
        
        # no perms
        self.assertFalse(group_has_any_perms(group0, object0))
        self.assertFalse(group_has_any_perms(group0, object0, ['Perm1', 'Perm2']))
        
        # single perm
        group0.grant("Perm1", object0)
        group1.grant("Perm2", object0)
        self.assertTrue(group_has_any_perms(group0, object0))
        self.assertTrue(group_has_any_perms(group1, object0))
        self.assertTrue(group_has_any_perms(group0, object0, ['Perm1', 'Perm2']))
        self.assertTrue(group_has_any_perms(group1, object0, ['Perm1', 'Perm2']))
        group0.revoke_all(object0)
        group1.revoke_all(object0)
    
    def test_get_groups(self):
        """
        Tests retrieving list of Groups with perms on an object
        """
        group0 = self.test_save('TestGroup0')
        group1 = self.test_save('TestGroup1')
        
        group0.grant('Perm1', object0)
        group0.grant('Perm3', object1)
        group1.grant('Perm2', object1)
        
        self.assert_(group0 in get_groups(object0))
        self.assertFalse(group1 in get_groups(object0))
        self.assert_(group0 in get_groups(object1))
        self.assert_(group1 in get_groups(object1))
        self.assert_(len(get_groups(object1))==2)
    
    def test_get_groups_any(self):
        """
        Tests retrieving list of groups with perms on an object
        """
        group0 = self.test_save('TestGroup0')
        group1 = self.test_save('TestGroup1')
        
        group0.set_perms(['Perm1', 'Perm2'], object0)
        group0.set_perms(['Perm1', 'Perm3'], object1)
        group1.set_perms(['Perm2'], object1)
        
        # no perms
        self.assertFalse(user1 in get_groups_any(object0, ['Perm1']))
        
        # explicit any perms
        self.assert_(group0 in get_groups_any(object0))
        self.assert_(group0 in get_groups_any(object1))
        self.assertFalse(group1 in get_groups_any(object0))
        self.assert_(group1 in get_groups_any(object1))
        
        # has perms, but not the right one
        self.assertFalse(group0 in get_groups_any(object0, ['Perm3']))
        
        # has one perm, but not all
        self.assert_(group0 in get_groups_any(object0, ['Perm1','Perm3']))
        self.assert_(group0 in get_groups_any(object1, ['Perm1','Perm2']))
        
        # has single perm
        self.assert_(group0 in get_groups_any(object0, ['Perm1']))
        self.assert_(group0 in get_groups_any(object0, ['Perm2']))
        self.assert_(group1 in get_groups_any(object1, ['Perm2']))
        
        # has multiple perms
        self.assert_(group0 in get_groups_any(object0, ['Perm1','Perm2']))
        self.assert_(group0 in get_groups_any(object1, ['Perm1','Perm3']))    
    
    def test_get_groups_all(self):
        """
        Tests retrieving list of groups with perms on an object
        """
        group0 = self.test_save('TestGroup0')
        group1 = self.test_save('TestGroup1')
        
        group0.set_perms(['Perm1', 'Perm2'], object0)
        group0.set_perms(['Perm1', 'Perm3'], object1)
        group1.set_perms(['Perm2'], object1)
        
        # no perms
        self.assertFalse(group1 in get_groups_all(object0, ['Perm1']))
        
        # has perms, but not the right one
        self.assertFalse(group0 in get_groups_all(object0, ['Perm3']))
        
        # has one perm, but not all
        self.assertFalse(group0 in get_groups_all(object0, ['Perm1','Perm3']))
        self.assertFalse(group0 in get_groups_all(object1, ['Perm1','Perm2']))
        
        # has single perm
        self.assert_(group0 in get_groups_all(object0, ['Perm1']))
        self.assert_(group0 in get_groups_all(object0, ['Perm2']))
        self.assert_(group1 in get_groups_all(object1, ['Perm2']))
        
        # has multiple perms
        self.assert_(group0 in get_groups_all(object0, ['Perm1','Perm2']))
        self.assert_(group0 in get_groups_all(object1, ['Perm1','Perm3']))

    
    def test_user_get_objects_any_perms(self):
        """
        Test filtering objects
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create(name='test2')
        object2.save()
        object3 = TestModel.objects.create(name='test3')
        object3.save()
        object4 = TestModel.objects.create(name='test4')
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        group1.grant('Perm4', object3)
        user0.grant('Perm4', object4)
        
        # retrieve single perm
        self.assert_(object0 in user0.get_objects_any_perms(TestModel, ['Perm1']))
        self.assert_(object1 in user0.get_objects_any_perms(TestModel, ['Perm2']))
        self.assert_(object2 in user1.get_objects_any_perms(TestModel, ['Perm3']))
        self.assert_(object3 in user1.get_objects_any_perms(TestModel, ['Perm4']))
        
        # retrieve multiple perms
        query = user0.get_objects_any_perms(TestModel, ['Perm1', 'Perm2', 'Perm3'])
        self.assert_(object0 in query)
        self.assert_(object1 in query)
        self.assertEqual(2, query.count())
        query = user1.get_objects_any_perms(TestModel, ['Perm1', 'Perm3', 'Perm4'])
        self.assert_(object2 in query)
        self.assert_(object3 in query)
        self.assertEqual(2, query.count())
        
        # mix of group and users
        query = user0.get_objects_any_perms(TestModel, ['Perm1', 'Perm4'])
        self.assert_(object0 in query)
        self.assert_(object4 in query)
        self.assertEqual(2, query.count())
        
        # retrieve no results
        query = user0.get_objects_any_perms(TestModel, ['Perm3'])
        self.assertEqual(0, query.count())
        query = user1.get_objects_any_perms(TestModel, ['Perm1'])
        self.assertEqual(0, query.count())
        
        # extra kwargs
        query = user0.get_objects_any_perms(TestModel, ['Perm1', 'Perm2', 'Perm3']).filter(name='test0')
        self.assert_(object0 in query)
        self.assertEqual(1, query.count())
        
        # exclude groups
        query = user0.get_objects_any_perms(TestModel, ['Perm1', 'Perm4'], groups=False)
        self.assert_(object4 in query)
        self.assertEqual(1, query.count())
    
    def test_user_has_any_perms_on_model(self):
        """
        Test checking if a user has any of the perms on any instance of the model
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create()
        object2.save()
        object3 = TestModel.objects.create()
        object3.save()
        object4 = TestModel.objects.create()
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        user0.grant('Perm4', object4)
        
        # check single perm
        self.assert_(user0.has_any_perms(TestModel, ['Perm1']))
        self.assert_(user0.has_any_perms(TestModel, ['Perm2']))
        self.assert_(user1.has_any_perms(TestModel, ['Perm3']))
        
        # check multiple perms
        self.assert_(user0.has_any_perms(TestModel, ['Perm1', 'Perm4']))
        self.assert_(user0.has_any_perms(TestModel, ['Perm1', 'Perm2']))
        self.assert_(user1.has_any_perms(TestModel, ['Perm3', 'Perm4']))
        
        # no results
        self.assertFalse(user0.has_any_perms(TestModel, ['Perm3']))
        self.assertFalse(user1.has_any_perms(TestModel, ['Perm4']))
        
        # excluding group perms
        self.assert_(user0.has_any_perms(TestModel, ['Perm4'], False))
        self.assert_(user0.has_any_perms(TestModel, ['Perm2', 'Perm4'], False))
        self.assertFalse(user0.has_any_perms(TestModel, ['Perm2'], False))
    
    def test_user_has_all_perms_on_model(self):
        """
        Test checking if a user has all of the perms on any instance of the model
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create()
        object2.save()
        object3 = TestModel.objects.create()
        object3.save()
        object4 = TestModel.objects.create()
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm3', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        user0.grant('Perm4', object4)
        
        # check single perm
        self.assert_(user0.has_all_perms(TestModel, ['Perm1']))
        self.assert_(user0.has_all_perms(TestModel, ['Perm2']))
        self.assert_(user1.has_all_perms(TestModel, ['Perm3']))
        
        # check multiple perms
        self.assertFalse(user0.has_all_perms(TestModel, ['Perm1', 'Perm4']))
        self.assertFalse(user0.has_all_perms(TestModel, ['Perm1', 'Perm2']))
        self.assert_(user0.has_all_perms(TestModel, ['Perm1', 'Perm3']))
        self.assertFalse(user1.has_all_perms(TestModel, ['Perm3', 'Perm4']))
        
        # no results
        self.assertFalse(user1.has_all_perms(TestModel, ['Perm4']))
        
        # excluding group perms
        self.assert_(user0.has_all_perms(TestModel, ['Perm4'], False))
        self.assertFalse(user0.has_all_perms(TestModel, ['Perm2', 'Perm4'], False))
        self.assertFalse(user0.has_all_perms(TestModel, ['Perm2'], False))
    
    def test_group_has_any_perms_on_model(self):
        """
        Test checking if a user has any of the perms on any instance of the model
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create()
        object2.save()
        object3 = TestModel.objects.create()
        object3.save()
        object4 = TestModel.objects.create()
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        group0.grant('Perm4', object4)
        
        # check single perm
        self.assert_(group0.has_any_perms(TestModel, ['Perm1']))
        self.assert_(group0.has_any_perms(TestModel, ['Perm2']))
        self.assert_(group1.has_any_perms(TestModel, ['Perm3']))
        
        # check multiple perms
        self.assert_(group0.has_any_perms(TestModel, ['Perm1', 'Perm4']))
        self.assert_(group0.has_any_perms(TestModel, ['Perm1', 'Perm2']))
        self.assert_(group1.has_any_perms(TestModel, ['Perm3', 'Perm4']))
        
        # no results
        self.assertFalse(group0.has_any_perms(TestModel, ['Perm3']))
        self.assertFalse(group1.has_any_perms(TestModel, ['Perm4']))
    
    def test_group_has_all_perms_on_model(self):
        """
        Test checking if a user has all of the perms on any instance of the model
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create()
        object2.save()
        object3 = TestModel.objects.create()
        object3.save()
        object4 = TestModel.objects.create()
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm3', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        
        # check single perm
        self.assert_(group0.has_all_perms(TestModel, ['Perm1']))
        self.assert_(group0.has_all_perms(TestModel, ['Perm2']))
        self.assert_(group1.has_all_perms(TestModel, ['Perm3']))
        
        # check multiple perms
        self.assertFalse(group0.has_all_perms(TestModel, ['Perm1', 'Perm4']))
        self.assertFalse(group0.has_all_perms(TestModel, ['Perm1', 'Perm2']))
        self.assert_(group0.has_all_perms(TestModel, ['Perm1', 'Perm3']))
        self.assertFalse(group1.has_all_perms(TestModel, ['Perm3', 'Perm4']))
        
        # no results
        self.assertFalse(group1.has_all_perms(TestModel, ['Perm4']))
    
    def test_group_get_objects_any_perms(self):
        """
        Test filtering objects based only on the groups perms
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create(name='test2')
        object2.save()
        object3 = TestModel.objects.create(name='test3')
        object3.save()
        object4 = TestModel.objects.create(name='test4')
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object1)
        group1.grant('Perm3', object2)
        group1.grant('Perm4', object3)
        
        # implicit any
        self.assert_(object0 in group0.get_objects_any_perms(TestModel, ['Perm1']))
        self.assert_(object1 in group0.get_objects_any_perms(TestModel, ['Perm2']))
        self.assertFalse(object2 in group0.get_objects_any_perms(TestModel, ['Perm2']))
        self.assert_(object2 in group1.get_objects_any_perms(TestModel, ['Perm3']))
        self.assert_(object3 in group1.get_objects_any_perms(TestModel, ['Perm4']))
        
        # retrieve single perm
        self.assert_(object0 in group0.get_objects_any_perms(TestModel, ['Perm1']))
        self.assert_(object1 in group0.get_objects_any_perms(TestModel, ['Perm2']))
        self.assert_(object2 in group1.get_objects_any_perms(TestModel, ['Perm3']))
        self.assert_(object3 in group1.get_objects_any_perms(TestModel, ['Perm4']))
        
        # retrieve multiple perms
        query = group0.get_objects_any_perms(TestModel, ['Perm1', 'Perm2', 'Perm3'])
        self.assert_(object0 in query)
        self.assert_(object1 in query)
        self.assertEqual(2, query.count())
        query = group1.get_objects_any_perms(TestModel, ['Perm1', 'Perm3', 'Perm4'])
        self.assert_(object2 in query)
        self.assert_(object3 in query)
        self.assertEqual(2, query.count())
        
        # retrieve no results
        query = group0.get_objects_any_perms(TestModel, ['Perm3'])
        self.assertEqual(0, query.count())
        query = group1.get_objects_any_perms(TestModel, ['Perm1'])
        self.assertEqual(0, query.count())
        
        # extra kwargs
        query = group0.get_objects_any_perms(TestModel, ['Perm1', 'Perm2', 'Perm3']).filter( name='test0')
        self.assert_(object0 in query)
        self.assertEqual(1, query.count())
    
    def test_group_get_objects_all_perms(self):
        """
        Test filtering objects based only on the groups perms
        """
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create(name='test2')
        object2.save()
        object3 = TestModel.objects.create(name='test3')
        object3.save()
        object4 = TestModel.objects.create(name='test4')
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object0)
        group0.grant('Perm4', object1)
        group1.grant('Perm3', object2)
        group1.grant('Perm4', object2)
        
        # retrieve single perm
        self.assert_(object0 in group0.get_objects_all_perms(TestModel, ['Perm1']))
        self.assert_(object1 in group0.get_objects_all_perms(TestModel, ['Perm4']))
        self.assert_(object2 in group1.get_objects_all_perms(TestModel, ['Perm3']))
        self.assert_(object2 in group1.get_objects_all_perms(TestModel, ['Perm4']))
        
        # retrieve multiple perms
        query = group0.get_objects_all_perms(TestModel, ['Perm1', 'Perm2'])
        self.assert_(object0 in query)
        self.assertFalse(object1 in query)
        self.assertEqual(1, query.count())
        query = group1.get_objects_all_perms(TestModel, ['Perm3', 'Perm4'])
        self.assert_(object2 in query)
        self.assertFalse(object3 in query)
        self.assertEqual(1, query.count())
        
        # retrieve no results
        self.assertFalse(group0.get_objects_all_perms(TestModel, ['Perm3']).exists())
        self.assertFalse(group0.get_objects_all_perms(TestModel, ['Perm1','Perm4']).exists())
        self.assertFalse(group1.get_objects_all_perms(TestModel, ['Perm1']).exists())
        
        # extra kwargs
        query = group0.get_objects_all_perms(TestModel, ['Perm1', 'Perm2']).filter( name='test0')
        self.assert_(object0 in query)
        self.assertEqual(1, query.count())
    
    def test_group_get_all_objects_any_perms(self):
        group0 = self.test_save('TestGroup0', user0)
        group1 = self.test_save('TestGroup1', user1)
        
        object2 = TestModel.objects.create(name='test2')
        object2.save()
        object3 = TestModel.objects.create(name='test3')
        object3.save()
        object4 = TestModel.objects.create(name='test4')
        object4.save()
        
        group0.grant('Perm1', object0)
        group0.grant('Perm2', object1)
        group0.grant('Perm4', object1)
        
        perm_dict = group0.get_all_objects_any_perms()
        self.assert_(isinstance(perm_dict, (dict,)))
        self.assert_(TestModel in perm_dict, perm_dict.keys())
        self.assert_(object0 in perm_dict[TestModel])
        self.assert_(object1 in perm_dict[TestModel])
        self.assertFalse(object2 in perm_dict[TestModel])
        self.assertFalse(object3 in perm_dict[TestModel])
        self.assertFalse(object4 in perm_dict[TestModel])
        
        # no perms
        perm_dict = group1.get_all_objects_any_perms()
        self.assert_(isinstance(perm_dict, (dict,)))
        self.assert_(TestModel in perm_dict, perm_dict.keys())
        self.assertEqual(0, perm_dict[TestModel].count())


class TestGroupViews(TestCase):
    perms = [u'Perm1', u'Perm2', u'Perm3', u'Perm4']
    
    def setUp(self):
        self.tearDown()
        
        User(id=1, username='anonymous').save()
        settings.ANONYMOUS_USER_ID=1
        
        self.user = User(id=2, username='tester0')
        self.user.set_password('secret')
        self.user.save()
        self.user1 = User(id=3, username='tester1')
        self.user1.set_password('secret')
        self.user1.save()
        
        self.object0 = TestModel.objects.create(name='test0')
        self.object0.save()
        self.object1 = TestModel.objects.create(name='test1')
        self.object1.save()
    
    def tearDown(self):
        User.objects.all().delete()
        TestModel.objects.all().delete()
        Group.objects.all().delete()

    def test_save(self, name='test'):
        """ Test saving an Group """
        group = Group(name=name)
        group.save()
        return group
    
    def test_view_list(self):
        """
        Test viewing list of Groups
        """
        user = self.user
        group = self.test_save()
        group0 = self.test_save(name='group1')
        group1 = self.test_save(name='group2')
        group2 = self.test_save(name='group3')
        c = Client()
        url = '/groups/'
        
        # anonymous user
        response = c.get(url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized user (user with admin on no groups)
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.get(url)
        self.assertEqual(403, response.status_code)
        
        # authorized (permission)
        user.grant('admin', group)
        user.grant('admin', group1)
        response = c.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/list.html')
        groups = response.context['groups']
        self.assert_(group in groups)
        self.assert_(group1 in groups)
        self.assertEqual(2, len(groups))
        
        # authorized (superuser)
        user.revoke('admin', group0)
        user.revoke('admin', group1)
        user.is_superuser = True
        user.save()
        response = c.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/list.html')
        groups = response.context['groups']
        self.assert_(group in groups)
        self.assert_(group0 in groups)
        self.assert_(group1 in groups)
        self.assert_(group2 in groups)
        self.assertEqual(4, len(groups))
    
    def test_view_detail(self):
        """
        Test Viewing the detail for a Group
        
        Verifies:
            * 200 returned for valid group
            * 404 returned for invalid group
        """
        user = self.user
        group = self.test_save()
        c = Client()
        url = '/group/%s/'
        args = group.id
        
        # anonymous user
        response = c.get(url % args, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized user
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.get(url % args)
        self.assertEqual(403, response.status_code)
        
        # invalid usergroup
        response = c.get(url % "DoesNotExist")
        self.assertEqual(404, response.status_code)
        
        # authorized (permission)
        grant(user, 'admin', group)
        response = c.get(url % args)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/detail.html')
        
        # authorized (superuser)
        response = c.get(url % args)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/detail.html')

    def test_view_edit(self):
        user = self.user
        group = self.test_save()
        c = Client()
        url = '/group/%s/'
        
        # anonymous user
        response = c.post(url % group.id, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized user
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.post(url % group.id)
        self.assertEqual(403, response.status_code)
        
        # invalid usergroup
        response = c.post(url % "DoesNotExist")
        self.assertEqual(404, response.status_code)
        
        # get form - authorized (permission)
        # XXX need to implement Class wide permission for creating editing groups
        #grant(user, 'admin', group)
        #response = c.post(url % group.id)
        #self.assertEqual(200, response.status_code)
        #self.assertEquals('text/html; charset=utf-8', response['content-type'])
        #self.assertTemplateUsed(response, 'group/edit.html')
        
        # get form - authorized (permission)
        grant(user, 'admin', group)
        response = c.post(url % group.id)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/edit.html')
        
        # get form - authorized (superuser)
        user.revoke('admin', group)
        user.is_superuser = True
        user.save()
        response = c.post(url % group.id)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/edit.html')
        
        # missing name
        data = {'id':group.id}
        response = c.post(url % group.id, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        
        # successful edit
        data = {'id':group.id, 'name':'EDITED_NAME'}
        response = c.post(url % group.id, data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/group_row.html')
        group = Group.objects.get(id=group.id)
        self.assertEqual('EDITED_NAME', group.name)
    
    def test_view_create(self):
        """
        Test creating a new Group
        """
        user = self.user
        group = self.test_save()
        c = Client()
        url = '/group/'
        
        # anonymous user
        response = c.post(url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized user
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.post(url)
        self.assertEqual(403, response.status_code)
        
        # get form - authorized (permission)
        # XXX need to implement Class level permissions
        #grant(user, 'admin', group)
        #response = c.post(url % group.id)
        #self.assertEqual(200, response.status_code)
        #self.assertEquals('text/html; charset=utf-8', response['content-type'])
        #self.assertTemplateUsed(response, 'group/edit.html')
        
        # get form - authorized (superuser)
        user.revoke('admin', group)
        user.is_superuser = True
        user.save()
        response = c.post(url)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/edit.html')
        
        # missing name
        data = {'id':group.id}
        response = c.post(url)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/edit.html')
        
        # successful edit
        data = {'name':'ADD_NEW_GROUP'}
        response = c.post(url, data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/group_row.html')
        self.assert_(Group.objects.filter(name='ADD_NEW_GROUP').exists())
    
    def test_view_delete(self):
        """
        Test deleting a usergroup
        
        Verifies:
            * group is deleted
            * all associated permissions are deleted
        """
        user = self.user
        group0 = self.test_save()
        group1 = self.test_save(name='test2')
        c = Client()
        url = '/group/%s/'
        
        # anonymous user
        response = c.delete(url % group0.id, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized user
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.delete(url % group0.id)
        self.assertEqual(403, response.status_code)
        
        # invalid usergroup
        response = c.delete(url % "DoesNotExist")
        self.assertEqual(404, response.status_code)
        
        # get form - authorized (permission)
        grant(user, 'admin', group0)
        response = c.delete(url % group0.id)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertFalse(Group.objects.filter(id=group0.id).exists())
        self.assertEqual('1', response.content)
        
        # get form - authorized (superuser)
        user.is_superuser = True
        user.save()
        response = c.delete(url % group1.id)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertFalse(Group.objects.filter(id=group1.id).exists())
        self.assertEqual('1', response.content)
    
    def test_view_add_user(self):
        """
        Test view for adding a user:
        
        Verifies:
            * request from unauthorized user results in 403
            * GET returns a 200 code, response is html
            * POST with a user id adds user, response is html for user
            * POST without user id returns error as json
            * POST for invalid user id returns error as json
            * adding user a second time returns error as json
        """
        user = self.user
        group = self.test_save()
        c = Client()
        url = '/group/%d/user/add/'
        args = group.id
        
        # anonymous user
        response = c.get(url % args, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.get(url % args)
        self.assertEqual(403, response.status_code)
        response = c.post(url % args)
        self.assertEqual(403, response.status_code)
        
        # authorized post (perm granted)
        grant(user, 'admin', group)
        response = c.get(url % args)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/add_user.html')
        
        # authorized post (superuser)
        revoke(user, 'admin', group)
        user.is_superuser = True
        user.save()
        response = c.get(url % args)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'group/add_user.html')
        
        # missing user id
        response = c.post(url % args)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        
        # invalid user
        response = c.post(url % args, {'user':0})
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        
        # valid post
        data = {'user':user.id}
        response = c.post(url % args, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'permissions/user_row.html')
        self.assert_(group.user_set.filter(id=user.id).exists())
        
        # same user again
        response = c.post(url % args, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertEquals(group.user_set.filter(id=user.id).count(), 1)
    
    def test_view_remove_user(self):
        """
        Test view for adding a user:
        
        Verifies:
            * GET redirects user to 405
            * POST with a user id remove user, returns 1
            * POST without user id returns error as json
            * users lacking perms receive 403
            * removing user not in group returns error as json
            * removing user that does not exist returns error as json
            * user loses all permissions when removed from group
        """
        user = self.user
        group = self.test_save()
        c = Client()
        group.user_set.add(user)
        url = '/group/%d/user/remove/'
        args = group.id
        
        # anonymous user
        response = c.get(url % args, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # invalid permissions
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.get(url % args)
        self.assertEqual(403, response.status_code)
        response = c.post(url % args)
        self.assertEqual(403, response.status_code)
        
        # authorize and login
        grant(user, 'admin', group)
        
        # invalid method
        response = c.get(url % args)
        self.assertEqual(405, response.status_code)
        
        # valid request (perm)
        data = {'user':user.id}
        response = c.post(url % args, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertEqual('1', response.content)
        self.assertFalse(group.user_set.filter(id=user.id).exists())
        self.assertEqual([], user.get_perms(group))
        
        # valid request (superuser)
        revoke(user, 'admin', group)
        user.is_superuser = True
        user.save()
        group.user_set.add(user)
        response = c.post(url % args, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertEqual('1', response.content)
        self.assertFalse(group.user_set.filter(id=user.id).exists())
        
        # remove user again
        response = c.post(url % args, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertFalse(group.user_set.filter(id=user.id).exists())
        self.assertNotEqual('1', response.content)
        
        # remove invalid user
        response = c.post(url % args, {'user':0})
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertNotEqual('1', response.content)
    
    def test_view_update_permissions(self):
        """
        Tests setting permissions for a user
        
        Verifies:
            * request from unauthorized user results in 403
            * GET returns a 200 code, response is html
            * POST with a user id adds user, response is html for user
            * POST without user_id or group_id returns error as json
            * POST with both a user_id and group_id returns error as json
            * POST for invalid user id returns error as json
            * POST for invalid group_id returns error as json
            * adding user a second time returns error as json
            * POST with a user_id adds user, response is html for user
            * POST with a group_id adds user, response is html for user
            * perms added to appropriate models
        """
        user = self.user
        group = self.test_save()
        group.user_set.add(user)
        group1 = self.test_save('other_group')
        
        c = Client()
        url = '/group/%d/permissions/user/%s/'
        url_post = '/group/%d/permissions/'
        args = (group.id, user.id)
        args_post = group.id
        
        # anonymous user
        response = c.get(url % args, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'registration/login.html')
        
        # unauthorized
        self.assert_(c.login(username=user.username, password='secret'))
        response = c.get(url % args)
        self.assertEqual(403, response.status_code)
        response = c.post(url % args)
        self.assertEqual(403, response.status_code)
        
        # authorized post (perm granted)
        grant(user, 'admin', group)
        response = c.get(url % args, {'user':user.id})
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'permissions/form.html')
        
        # authorized post (superuser)
        revoke(user, 'admin', group)
        user.is_superuser = True
        user.save()
        response = c.get(url % args, {'user':user.id})
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'permissions/form.html')
    
        # invalid user (GET)
        response = c.get(url % (group.id, -1))
        self.assertEqual(404, response.status_code)
        
        # invalid group (GET)
        response = c.get(url % (-1, user.id))
        self.assertEqual(404, response.status_code)
        
        # invalid user (POST)
        data = {'permissions':['admin'], 'user':-1}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertNotEquals('1', response.content)
        
        # invalid group (POST)
        data = {'permissions':['admin'], 'group':-1}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertNotEquals('1', response.content)
        
        # user and group (POST)
        data = {'permissions':['admin'], 'user':user.id, 'group':group1.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertNotEquals('1', response.content)
        
        # invalid permission
        data = {'permissions':['DoesNotExist'], 'user':user.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('application/json', response['content-type'])
        self.assertNotEquals('1', response.content)
        
        # valid post user
        data = {'permissions':['admin'], 'user':user.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'permissions/user_row.html')
        self.assert_(user.has_perm('admin', group))
        self.assertEqual(['admin'], get_user_perms(user, group))
        
        # valid post no permissions user
        data = {'permissions':[], 'user':user.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEqual([], get_user_perms(user, group))
        
        # valid post group
        data = {'permissions':['admin'], 'group':group1.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEquals('text/html; charset=utf-8', response['content-type'])
        self.assertTemplateUsed(response, 'permissions/user_row.html')
        self.assertEqual(['admin'], group1.get_perms(group))
        
        # valid post no permissions group
        data = {'permissions':[], 'group':group1.id}
        response = c.post(url_post % args_post, data)
        self.assertEqual(200, response.status_code)
        self.assertEqual([], group1.get_perms(group))
