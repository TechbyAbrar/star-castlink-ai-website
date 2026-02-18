from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsOwnerOrSuperuser(BasePermission):
    __slots__ = ()

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_superuser or obj.owner_id == user.id


class IsSuperuserOrReadOnly(BasePermission):
    __slots__ = ()

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)
from rest_framework.permissions import BasePermission


class IsAgent(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "Agent"
        )


class IsClient(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "Client"
        )
