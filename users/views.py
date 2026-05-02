from django.contrib.auth import authenticate, logout
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


class RegisterAPIView(generics.CreateAPIView):
    """POST /api/users/register/ — create a new user."""
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def login_view(request):
    if request.method == 'GET':
        return Response({'detail': 'POST username and password to log in.'})

    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return Response({
            'token': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        })
    return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    if request.method == 'GET':
        return Response({'detail': 'POST to logout (must be authenticated).'})
    logout(request)
    return Response({'message': 'Logged out.'})
