#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RBAC Permission System
نظام الصلاحيات القائم على الأدوار
"""

from typing import Dict, List, Optional, Any, Tuple
from supabase import Client

class PermissionManager:
    """مدير نظام الصلاحيات"""
    
    def __init__(self, supabase: Client):
        self.supabase = supabase
    
    def create_role(self, name: str, description: str, permissions: Dict[str, bool]) -> Tuple[bool, str]:
        """إنشاء صلاحية جديدة"""
        try:
            # التحقق من عدم وجود الصلاحية مسبقاً
            result = self.supabase.table('roles').select('id').eq('name', name).execute()
            if result.data:
                return False, "اسم الصلاحية موجود مسبقاً"
            
            data = {
                'name': name,
                'description': description,
                'permissions': permissions
            }
            self.supabase.table('roles').insert(data).execute()
            return True, "تم إنشاء الصلاحية بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def update_role(self, role_id: int, name: Optional[str] = None, 
                   description: Optional[str] = None, 
                   permissions: Optional[Dict[str, bool]] = None) -> Tuple[bool, str]:
        """تحديث صلاحية موجودة"""
        try:
            update_data = {}
            if name:
                update_data['name'] = name
            if description:
                update_data['description'] = description
            if permissions:
                update_data['permissions'] = permissions
            
            if not update_data:
                return False, "لا توجد بيانات للتحديث"
            
            self.supabase.table('roles').update(update_data).eq('id', role_id).execute()
            return True, "تم تحديث الصلاحية بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def delete_role(self, role_id: int) -> Tuple[bool, str]:
        """حذف صلاحية"""
        try:
            # التحقق من عدم استخدام الصلاحية
            result = self.supabase.table('user_roles').select('id').eq('role_id', role_id).execute()
            if result.data:
                return False, "لا يمكن حذف الصلاحية لأنها مستخدمة من قبل مستخدمين"
            
            self.supabase.table('roles').delete().eq('id', role_id).execute()
            return True, "تم حذف الصلاحية بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def get_all_roles(self) -> List[Dict[str, Any]]:
        """الحصول على جميع الصلاحيات"""
        try:
            result = self.supabase.table('roles').select('*').execute()
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ خطأ في الحصول على الصلاحيات: {e}")
            return []
    
    def get_role_by_id(self, role_id: int) -> Optional[Dict[str, Any]]:
        """الحصول على صلاحية محددة"""
        try:
            result = self.supabase.table('roles').select('*').eq('id', role_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ خطأ في الحصول على الصلاحية: {e}")
            return None
    
    def assign_role_to_user(self, user_id: int, role_id: int) -> Tuple[bool, str]:
        """إسناد صلاحية لمستخدم"""
        try:
            # التحقق من وجود المستخدم
            user_result = self.supabase.table('users').select('id').eq('id', user_id).execute()
            if not user_result.data:
                return False, "المستخدم غير موجود"
            
            # التحقق من وجود الصلاحية
            role_result = self.supabase.table('roles').select('id').eq('id', role_id).execute()
            if not role_result.data:
                return False, "الصلاحية غير موجودة"
            
            # إسناد الصلاحية
            data = {
                'user_id': user_id,
                'role_id': role_id
            }
            self.supabase.table('user_roles').insert(data).execute()
            return True, "تم إسناد الصلاحية بنجاح"
        except Exception as e:
            if 'duplicate key' in str(e).lower():
                return False, "الصلاحية مسندة بالفعل لهذا المستخدم"
            return False, f"خطأ: {str(e)}"
    
    def remove_role_from_user(self, user_id: int, role_id: int) -> Tuple[bool, str]:
        """إزالة صلاحية من مستخدم"""
        try:
            self.supabase.table('user_roles').delete().eq('user_id', user_id).eq('role_id', role_id).execute()
            return True, "تم إزالة الصلاحية بنجاح"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def get_user_roles(self, user_id: int) -> List[Dict[str, Any]]:
        """الحصول على صلاحيات مستخدم محدد"""
        try:
            result = self.supabase.table('user_roles').select('*, roles(*)').eq('user_id', user_id).execute()
            return [item['roles'] for item in result.data] if result.data else []
        except Exception as e:
            print(f"❌ خطأ في الحصول على صلاحيات المستخدم: {e}")
            return []
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """الحصول على جميع صلاحيات المستخدم مدمجة"""
        try:
            # الحصول على جميع الأدوار
            roles = self.get_user_roles(user_id)
            
            # دمج جميع الصلاحيات
            merged_permissions = {
                'upload': False,
                'delete': False,
                'edit': False,
                'manage_users': False,
                'view_all': False
            }
            
            for role in roles:
                permissions = role.get('permissions', {})
                for key, value in permissions.items():
                    if value:  # إذا كانت الصلاحية true في أي دور
                        merged_permissions[key] = True
            
            return merged_permissions
        except Exception as e:
            print(f"❌ خطأ في دمج الصلاحيات: {e}")
            return {}
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """التحقق من صلاحية معينة للمستخدم"""
        try:
            # التحقق من الأدمن أولاً
            user_result = self.supabase.table('users').select('is_admin').eq('id', user_id).execute()
            if user_result.data and user_result.data[0]['is_admin']:
                return True  # الأدمن له جميع الصلاحيات
            
            # الحصول على صلاحيات المستخدم
            permissions = self.get_user_permissions(user_id)
            return permissions.get(permission, False)
        except Exception as e:
            print(f"❌ خطأ في التحقق من الصلاحية: {e}")
            return False
    
    def get_users_with_role(self, role_id: int) -> List[Dict[str, Any]]:
        """الحصول على جميع المستخدمين الذين لديهم صلاحية معينة"""
        try:
            result = self.supabase.table('user_roles').select('*, users(*)').eq('role_id', role_id).execute()
            return [item['users'] for item in result.data] if result.data else []
        except Exception as e:
            print(f"❌ خطأ في الحصول على المستخدمين: {e}")
            return []
    
    def get_all_users_with_permissions(self) -> List[Dict[str, Any]]:
        """الحصول على جميع المستخدمين مع صلاحياتهم"""
        try:
            users_result = self.supabase.table('users').select('*').execute()
            users = users_result.data if users_result.data else []
            
            # إضافة الصلاحيات لكل مستخدم
            for user in users:
                user['roles'] = self.get_user_roles(user['id'])
                user['permissions'] = self.get_user_permissions(user['id'])
            
            return users
        except Exception as e:
            print(f"❌ خطأ في الحصول على المستخدمين: {e}")
            return []

# الصلاحيات الافتراضية المتاحة
DEFAULT_PERMISSIONS = {
    'upload': 'رفع الملفات',
    'delete': 'حذف الملفات',
    'edit': 'تعديل الملفات',
    'manage_users': 'إدارة المستخدمين',
    'view_all': 'عرض جميع الملفات'
}

def get_permission_description(permission: str) -> str:
    """الحصول على وصف الصلاحية"""
    return DEFAULT_PERMISSIONS.get(permission, permission)
