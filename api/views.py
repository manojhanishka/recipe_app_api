from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, JSONParser, FormParser
from rest_framework import generics, permissions
from .models import (CustomUser,ProfileImage,UserPreference,DietaryRestriction,Cuisine,MajorIngredient,Like,Course,Tag)
from rest_framework import status,permissions
from .serializers import (UserSerializer,LoginSerializer,ProfileImageSerializer,
                          UserPreferenceSerializer,CourseSerializer,
                          UserProfileSerializer,UserProfileUpdateSerializer,
                          RecipeSerializer,DietaryRestrictionSerializer,CuisineSerializer,
                          MajorIngredientSerializer,LikeSerializer,TagSerializer)
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Recipe,SavedRecipe
from django.shortcuts import get_object_or_404
from django.db.models import Q
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models.functions import Lower
from django.db.models import Case, When
from .utils import (
    Preprocess,normalize_ingredient_name,generate_verification_code,send_verification_email,
    generate_reset_code,send_reset_email
    )
from .AI import start,recommend_similar_recipes,generate_recipe_by_ings


def hello_world(request):
    return JsonResponse({"message": "Hello, World!"})


class RegisterUserView(generics.CreateAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


class ResendVerificationCodeAPIView(APIView):
    permission_classes = []  # Or AllowAny if you want

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if user.email_verified:
            return Response({"message": "Email is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate new verification code and save it
        code = generate_verification_code()
        user.verification_code = code
        user.save()

        # Send verification email
        send_verification_email(user.email, code)

        return Response({"message": "Verification code resent successfully."})
    
    
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

User = get_user_model()

class GoogleLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('id_token')

        if not token:
            return Response({'error': 'ID token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GOOGLE_CLIENT_ID)

            email = idinfo.get('email')
            name = idinfo.get('name')

            if not email:
                return Response({'error': 'Email not found in Google token'}, status=400)

            # Create or get user
            user, created = User.objects.get_or_create(email=email, defaults={
                'username': f"{email.split('@')[0]}_{User.objects.count()}",
                'email_verified': True,  # ✅ TRUST GOOGLE
                'is_active': True 
            })

            if created:
                user.save()


            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'phone': user.phone,
                }
            })

        except ValueError:
            return Response({'error': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)
        


class ResendResetCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
            code = generate_reset_code()
            user.reset_code = code
            user.save()

            send_reset_email(email, code)

            return Response({"message": "Reset code resent successfully."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
User = get_user_model()

class VerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        try:
            user = User.objects.get(email=email)
            if user.verification_code == code:
                user.email_verified = True
                user.is_active = True
                user.verification_code = None  # Clear code
                user.save()
                return Response({'message': 'Email verified successfully'}, status=200)
            else:
                return Response({'error': 'Invalid code'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        

class RequestPasswordResetAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            code = generate_reset_code()
            user.reset_code = code
            user.save()
            send_reset_email(user.email, code)
            return Response({"message": "Reset code sent to email"}, status=200)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)
        

class CheckResetCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')

        if not email or not code:
            return Response({'error': 'Email and code are required.'}, status=400)

        try:
            user = User.objects.get(email=email)
            if user.reset_code == code:
                return Response({'message': 'Reset code is valid.'}, status=200)
            else:
                return Response({'error': 'Invalid reset code.'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=404)

class ConfirmResetCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        try:
            user = User.objects.get(email=email)
            if user.reset_code == code:
                user.set_password(new_password)
                user.reset_code = None
                user.save()
                return Response({"message": "Password reset successful"}, status=200)
            else:
                return Response({"error": "Invalid reset code"}, status=400)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]  
    parser_classes = [MultiPartParser, FormParser] 

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Profile updated successfully", "data": serializer.data})
        return Response(serializer.errors, status=400)
    

class ProfileImageListView(APIView):
    authentication_classes = []
    permission_classes = []    

    def get(self, request):
        images = ProfileImage.objects.all()
        serializer = ProfileImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)
    
    

class AddRecipeView(generics.CreateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only superusers can add recipes.")

        recipe = serializer.save()

        self.assign_major_ingredients(recipe)

    def assign_major_ingredients(self, recipe):
        major_names = MajorIngredient.objects.values_list('name', flat=True)
        recipe_ingredients = recipe.ingredients.values_list('ingredient', flat=True)

        for major in major_names:
            for ing in recipe_ingredients:
                if major.lower() in ing.lower():
                    major_obj = MajorIngredient.objects.get(name=major)
                    recipe.major_ingredients.add(major_obj)

class UpdateRecipeView(generics.UpdateAPIView):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser] 

    def update(self, request, *args, **kwargs):
        # Only superusers can update recipes
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can update recipes.")
        
        return super().update(request, *args, **kwargs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)  # Handle invalid ID
    saved_recipe, created = SavedRecipe.objects.get_or_create(user=request.user, recipe=recipe)
    if created:
        return JsonResponse({"message": "Recipe saved successfully"})
    return JsonResponse({"message": "Recipe already saved"})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_saved_recipe(request, recipe_id):
    recipe = Recipe.objects.filter(id=recipe_id).first()  # Check if recipe exists
    if not recipe:
        return JsonResponse({"error": "Recipe not found"}, status=404)

    SavedRecipe.objects.filter(user=request.user, recipe=recipe).delete()
    return JsonResponse({"message": "Recipe removed from saved list"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_saved_recipes(request):
    user = request.user
    saved_recipes = Recipe.objects.filter(saved_by_users__user=user)
    if not saved_recipes.exists():
        return JsonResponse({"message": "No saved recipes found"}, status=404)
        
    serializer = RecipeSerializer(saved_recipes, many=True,context={'request': request})
    return Response({"recipes": serializer.data})




@api_view(['GET'])
def get_all_recipes(request):
    recipes = Recipe.objects.all()
    serializer = RecipeSerializer(recipes, many=True,context={'request': request})
    return Response(serializer.data, status=200)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Ensure only authenticated users can access
def get_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)  # Fetch the recipe or return 404
    serializer = RecipeSerializer(recipe,context={'request': request})  # Serialize the recipe data
    return Response(serializer.data)  # Return JSON response



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_recipes(request):
    query = request.GET.get('q', '').strip().lower()  # Convert query to lowercase
    if not query:
        return Response({"message": "No search query provided"}, status=400)

    # Annotate fields to lowercase and then filter
    recipes = Recipe.objects.annotate(
        lower_title=Lower('title'),
        lower_cuisine_name=Lower('cuisine__name'),
        lower_course_name=Lower('course__name')
    ).filter(
        Q(lower_title__icontains=query) |
        Q(lower_cuisine_name__icontains=query) |
        Q(lower_course_name__icontains=query)
    ).distinct()


    serializer = RecipeSerializer(recipes, many=True,context={'request': request})
    return Response(serializer.data)

# views.py

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"detail": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)

        except TokenError as e:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_saved_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    is_saved = SavedRecipe.objects.filter(user=request.user, recipe=recipe).exists()
    return JsonResponse({'is_saved': is_saved})


class UserPreferenceListView(generics.ListCreateAPIView):
    queryset = UserPreference.objects.all()
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        print(self.request.user)
        # Return only the preferences of the logged-in user
        return UserPreference.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Associate the new preference with the logged-in user
        # Ensure that dietary restrictions, nutrients, and cuisines are included in the request data
        dietary_restrictions = self.request.data.get('dietary_restrictions', [])
        preferred_cuisines = self.request.data.get('preferred_cuisines', [])

        # Check if the provided preferences are valid
        dietary_restrictions_objects = DietaryRestriction.objects.filter(id__in=dietary_restrictions)
        preferred_cuisines_objects = Cuisine.objects.filter(id__in=preferred_cuisines)

        if len(dietary_restrictions_objects) != len(dietary_restrictions):
            raise ValidationError("Some dietary restrictions are invalid.")
        if len(preferred_cuisines_objects) != len(preferred_cuisines):
            raise ValidationError("Some preferred cuisines are invalid.")

        # Create the UserPreference object and associate it with the user
        user_preference = serializer.save(user=self.request.user)

        # Set the related fields (dietary_restrictions, preferred_nutrients, preferred_cuisines)
        user_preference.dietary_restrictions.set(dietary_restrictions_objects)
        user_preference.preferred_cuisines.set(preferred_cuisines_objects)

        # Save the updated UserPreference object
        user_preference.save()

# PATCH or PUT: Update user's selected preferences (partial update allowed)
class UserPreferencePartialUpdateView(generics.UpdateAPIView):
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Get or create a preference object for the authenticated user
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Allow partial update with dietary_restrictions / preferred_cuisines
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


# DELETE: Clear user preferences
class UserPreferenceDeleteView(generics.DestroyAPIView):
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Get or create preference object for user
        preference, _ = UserPreference.objects.get_or_create(user=self.request.user)
        return preference

    def perform_destroy(self, instance):
        # Instead of deleting the object, just clear the many-to-many relations
        instance.dietary_restrictions.clear()
        instance.preferred_cuisines.clear()


# GET: Return all available cuisines and dietary restrictions
class AllPreferencesListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dietary = DietaryRestriction.objects.all()
        cuisines = Cuisine.objects.all()

        data = {
            "dietary_restrictions": DietaryRestrictionSerializer(dietary, many=True).data,
            "cuisines": CuisineSerializer(cuisines, many=True).data,
        }

        return Response(data)

    
class RecipeByMajorIngredientView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get the major ingredient name from the query params
        major_ingredient_name = request.query_params.get('ingredient', None)

        if major_ingredient_name:
            try:
                # Fetch the major ingredient from the database
                major_ingredient = MajorIngredient.objects.get(name=major_ingredient_name)
                # Fetch all recipes related to this major ingredient
                recipes = Recipe.objects.filter(major_ingredients=major_ingredient)
                serializer = RecipeSerializer(recipes, many=True,context={'request': request})
                return Response(serializer.data)
            except MajorIngredient.DoesNotExist:
                return Response({"detail": "Major ingredient not found."}, status=404)
        else:
            return Response({"detail": "Ingredient parameter is required."}, status=400)
        


class MajorIngredientListView(generics.ListAPIView):
    queryset = MajorIngredient.objects.all()
    serializer_class = MajorIngredientSerializer
    permission_classes = [permissions.IsAuthenticated]


# views.pyfrom .models import Recipe

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendations(request):
    try:
        username = request.user.username
        df = start(username)

        if df.empty:
            return Response({"message": "No recommendations available."}, status=404)

        # Get list of IDs from DataFrame in order
        recipe_ids = df['ID'].tolist()

        # Fetch recipes and map them to a dictionary with ID as key
        recipes = Recipe.objects.filter(id__in=recipe_ids)
        recipe_dict = {recipe.id: recipe for recipe in recipes}

        # Maintain the order from the recommendation DataFrame
        ordered_recipes = [recipe_dict[rid] for rid in recipe_ids if rid in recipe_dict]

        # Serialize the ordered recipes
        serializer = RecipeSerializer(ordered_recipes, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_similar_recipes(request, recipe_id):
    top_n = int(request.GET.get("top_n", 5))

    try:
        # Get recommended DataFrame
        recommended_df = recommend_similar_recipes(recipe_id, top_n=top_n)

        if recommended_df.empty:
            return Response({"message": "No similar recipes found."}, status=status.HTTP_404_NOT_FOUND)

        # Extract ordered list of recommended recipe IDs
        recommended_ids = recommended_df["ID"].tolist()

        # Fetch recipes and preserve order using Case/When
        preserved_order = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(recommended_ids)])
        recipes = Recipe.objects.filter(id__in=recommended_ids).order_by(preserved_order)

        # Serialize and return
        serializer = RecipeSerializer(recipes, many=True,context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LikeRecipeView(generics.CreateAPIView):
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        recipe_id = self.request.data.get('recipe')
        if not recipe_id:
            raise ValidationError({"recipe": "Recipe ID is required."})

        # Check if recipe exists
        try:
            recipe = Recipe.objects.get(id=recipe_id)
        except Recipe.DoesNotExist:
            raise ValidationError({"recipe": "Recipe not found."})

        # Prevent duplicate like (optional, your model unique_together enforces this but better to catch early)
        if Like.objects.filter(user=self.request.user, recipe=recipe).exists():
            raise ValidationError("You have already liked this recipe.")

        serializer.save(user=self.request.user, recipe=recipe)




class UnlikeRecipeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        recipe_id = request.data.get('recipe')
        if not recipe_id:
            return Response({"recipe": "Recipe ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            like = Like.objects.get(user=request.user, recipe_id=recipe_id)
        except Like.DoesNotExist:
            return Response({"detail": "You have not liked this recipe."}, status=status.HTTP_404_NOT_FOUND)

        like.delete()
        return Response({"detail": "Recipe unliked successfully."}, status=status.HTTP_200_OK)
    


class LikedRecipesView(generics.ListAPIView):
    serializer_class = RecipeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        liked_recipe_ids = Like.objects.filter(user=user).values_list('recipe_id', flat=True)
        return Recipe.objects.filter(id__in=liked_recipe_ids)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request  # Pass request to serializer
        return context

class FilteredAllRecipeListView(generics.ListAPIView):
    serializer_class = RecipeSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()

        cuisine_id = self.request.query_params.get('cuisine')
        course_id = self.request.query_params.get('course')
        dietary_id = self.request.query_params.get('dietary')
        tag_id = self.request.query_params.get('tag')

        if not any([cuisine_id, course_id, dietary_id, tag_id]):
            raise ValidationError("Provide at least one of 'cuisine', 'course', 'dietary', or 'tag' as query parameters.")

        if cuisine_id:
            queryset = queryset.filter(cuisine__id=cuisine_id)
        if course_id:
            queryset = queryset.filter(course__id=course_id)
        if dietary_id:
            queryset = queryset.filter(dietary_restrictions__id=dietary_id)
        if tag_id:
            queryset = queryset.filter(tags__id=tag_id)

        return queryset.distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
    

class FilteredRecipeListView(APIView):
    def post(self, request):
        recipe_ids = request.data.get('recipe_ids', [])
        if not recipe_ids:
            raise ValidationError("You must provide a list of 'recipe_ids' in the request body.")

        queryset = Recipe.objects.filter(id__in=recipe_ids)

        # Optional filters
        cuisine_ids = request.query_params.get('cuisine')
        course_ids = request.query_params.get('course')
        dietary_ids = request.query_params.get('dietary')
        tag_ids = request.query_params.get('tag')

        if cuisine_ids:
            cuisine_ids = [int(x) for x in cuisine_ids.split(',')]
            queryset = queryset.filter(cuisine__id__in=cuisine_ids)

        if course_ids:
            course_ids = [int(x) for x in course_ids.split(',')]
            queryset = queryset.filter(course__id__in=course_ids)

        if dietary_ids:
            dietary_ids = [int(x) for x in dietary_ids.split(',')]
            queryset = queryset.filter(dietary_restrictions__id__in=dietary_ids)

        if tag_ids:
            tag_ids = [int(x) for x in tag_ids.split(',')]
            queryset = queryset.filter(tags__id__in=tag_ids)

        queryset = queryset.distinct()
        serializer = RecipeSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)
    

class SortedRecipeListView(APIView):
    def post(self, request):
        ids = request.data.get("ids", [])
        sort_by = request.data.get("sort_by", None)  # "time" or "difficulty"

        if not isinstance(ids, list) or not ids:
            return Response({"error": "Please provide a non-empty list of recipe IDs."},
                            status=status.HTTP_400_BAD_REQUEST)

        recipes = Recipe.objects.filter(id__in=ids)
        recipe_list = list(recipes)
        p=Preprocess()

        if sort_by == "time":
            total_times = [r.total_time for r in recipe_list]
            time_values = p.preprocess_time(total_times)
            sorted_data = sorted(zip(recipe_list, time_values), key=lambda x: x[1])
            sorted_recipes = [item[0] for item in sorted_data]

        elif sort_by == "difficulty":
            difficulties = [r.difficulty_level for r in recipe_list]
            diff_values = p.preprocess_difflevel(difficulties)
            sorted_data = sorted(zip(recipe_list, diff_values), key=lambda x: x[1])
            sorted_recipes = [item[0] for item in sorted_data]

        else:
            sorted_recipes = recipe_list

        serializer = RecipeSerializer(sorted_recipes, many=True, context={"request": request})
        return Response(serializer.data)



class RecipeFilteredByUserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        recipe_ids = request.data.get('recipe_ids', [])
        if not recipe_ids:
            raise ValidationError("You must provide a list of 'recipe_ids' in the request body.")

        try:
            preferences = request.user.preferences
        except UserPreference.DoesNotExist:
            raise ValidationError("User preferences are not set.")

        # Start with given recipes
        queryset = Recipe.objects.filter(id__in=recipe_ids)

        # Apply user preferences filtering
        if preferences.dietary_restrictions.exists():
            queryset = queryset.filter(dietary_restrictions__in=preferences.dietary_restrictions.all())

        if preferences.preferred_cuisines.exists():
            queryset = queryset.filter(cuisine__in=preferences.preferred_cuisines.all())

        # Optional nutrient filtering can be added if recipe links to nutrients

        queryset = queryset.distinct()
        serializer = RecipeSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class RecipeSimilarityView(APIView):
    def post(self, request):
        user_ingredients = request.data.get('ingredients')  
        if not user_ingredients:
            return Response({"error": "Missing ingredients"}, status=400)
        if "," in user_ingredients:
            user_ingredients=user_ingredients.split(",")
            user_ingredients="".join([normalize_ingredient_name(i) for i in user_ingredients]).lower()
        else:
            user_ingredients=normalize_ingredient_name(user_ingredients)

            
        
        recipes = generate_recipe_by_ings([user_ingredients], request=request)
        return Response(recipes)

# Cuisine List View
class CuisineListView(generics.ListAPIView):
    queryset = Cuisine.objects.all()
    serializer_class = CuisineSerializer

# Course List View
class CourseListView(generics.ListAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

# DietaryRestriction List View
class DietaryRestrictionListView(generics.ListAPIView):
    queryset = DietaryRestriction.objects.all()
    serializer_class = DietaryRestrictionSerializer

class TagListView(generics.ListAPIView):
    queryset = Tag.objects.all()
    serializer_class=TagSerializer