from django.db import transaction

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SignupSerializer
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
        
