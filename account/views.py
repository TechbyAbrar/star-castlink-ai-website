from django.db import transaction

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (SignupSerializer, VerifyOTPSerializer, ResendVerifyOTPSerializer, LoginSerializer,
                          UserInfoSerializer, ForgetPasswordSerializer, VerifyForgetPasswordOTPSerializer, ResetPasswordSerializer)
from .utils import generate_tokens_for_user


class SignupAPIView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = generate_tokens_for_user(user)

        return Response(
            {   
                "success": "True",
                "message": "Account created successfully. OTP sent to email.",
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_verified": user.is_verified,
                },
                "tokens": tokens['access'],
            },
            status=status.HTTP_201_CREATED,
        )
        

class VerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        tokens = generate_tokens_for_user(user)

        return Response(
            {
                "success": True,
                "message": "OTP verified successfully.",
                "data": {
                    "tokens": {
                        "access": tokens["access"],
                    },
                    "user": {
                        "id": user.user_id,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_verified": user.is_verified,
                    },
                },
            },
            status=status.HTTP_200_OK,
        )
        
        
class ResendVerifyOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendVerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "A new OTP has been sent to your email.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
        
        
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = generate_tokens_for_user(user)
        user_data = UserInfoSerializer(user, context={"request": request}).data

        return Response(
            {
                "success": True,
                "message": "Login successful",
                "data": {
                    "user": user_data,
                    "tokens": {
                        "access": tokens["access"],
                        "refresh": tokens["refresh"],
                    },
                },
            },
            status=status.HTTP_200_OK,
        )



class ForgetPasswordView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "OTP sent to user email successfully.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
        
        
class VerifyForgetPasswordOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyForgetPasswordOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response_data = serializer.to_representation(serializer.validated_data)

        return Response(
            {
                "success": True,
                "message": "OTP verified successfully.",
                "data": response_data,
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Password reset successfully.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
