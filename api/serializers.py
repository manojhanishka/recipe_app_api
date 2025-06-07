from rest_framework import serializers
from .models import CustomUser,ProfileImage
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.conf import settings

from .models import (Recipe, Ingredient, Instruction, NutritionalInformation, 
                     ProfileImage,Equipment, Tag,
                       SubstituteIngredient,UserPreference, 
                       DietaryRestriction, 
                     Cuisine,Course,MajorIngredient,Like)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'phone', 'profile_pic', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        from .utils import generate_verification_code, send_verification_email

        code = generate_verification_code()

        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            phone=validated_data['phone'],
            password=validated_data['password'],
            is_active=False,  # Prevent login until verified
            verification_code=code
        )

        send_verification_email(user.email, code)
        return user

    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        user = authenticate(email=email, password=password)

        if user is None:
            raise serializers.ValidationError("Invalid email or password")

        tokens = RefreshToken.for_user(user)
        return {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone": user.phone
            },
            "access_token": str(tokens.access_token),
            "refresh_token": str(tokens)
        }
        
        
        
User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'profile_pic']
        read_only_fields = ['id', 'email']

    def get_profile_pic(self, obj):
        request = self.context.get('request')
        if obj.profile_pic and hasattr(obj.profile_pic, 'url'):
            return request.build_absolute_uri(obj.profile_pic.url)
        return ''


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)  # Optional password update

    class Meta:
        model = User
        fields = ['username', 'phone', 'profile_pic', 'password']

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])  # Hash password
        return super().update(instance, validated_data)
    
    
# New serializers for related models
class CuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ['id', 'name']

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'name']

class DietaryRestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietaryRestriction
        fields = ['id', 'name']

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['ingredient', 'quantity']

class InstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instruction
        fields = ['step']

class NutritionalInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionalInformation
        fields = ['calories', 'protein', 'carbs', 'fat']

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ['name']

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id','name']

class SubstituteIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteIngredient
        fields = ['ingredient', 'substitute', 'notes']
        
class RecipeSerializer(serializers.ModelSerializer):
    ingredients = IngredientSerializer(many=True)
    instructions = InstructionSerializer(many=True)
    nutritional_information = NutritionalInformationSerializer()
    equipment = EquipmentSerializer(many=True)
    tags = TagSerializer(many=True)
    substitutes = SubstituteIngredientSerializer(many=True)
    dietary_restrictions = serializers.PrimaryKeyRelatedField(
        queryset=DietaryRestriction.objects.all(), many=True
    )
    
    # Use nested serializers for read operations
    cuisine = CuisineSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    
    # Use write_only fields to accept IDs on create/update
    cuisine_id = serializers.PrimaryKeyRelatedField(
        queryset=Cuisine.objects.all(), write_only=True, source='cuisine'
    )
    course_id = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(), write_only=True, source='course'
    )
    
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = '__all__'

    def get_like_count(self, obj):
        return obj.like_count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            return obj.is_liked_by_user(request.user)
        return False

    def create(self, validated_data):
        # Extract nested write_only keys to the actual FK fields
        cuisine = validated_data.pop('cuisine', None)
        course = validated_data.pop('course', None)

        ingredients_data = validated_data.pop('ingredients')
        instructions_data = validated_data.pop('instructions')
        nutritional_data = validated_data.pop('nutritional_information')
        equipment_data = validated_data.pop('equipment')
        tags_data = validated_data.pop('tags')
        substitutes_data = validated_data.pop('substitutes')
        dietary_data = validated_data.pop('dietary_restrictions', [])

        recipe = Recipe.objects.create(cuisine=cuisine, course=course, **validated_data)
        recipe.dietary_restrictions.set(dietary_data)

        for ingredient in ingredients_data:
            Ingredient.objects.create(recipe=recipe, **ingredient)

        for instruction in instructions_data:
            Instruction.objects.create(recipe=recipe, **instruction)

        NutritionalInformation.objects.create(recipe=recipe, **nutritional_data)

        for equipment in equipment_data:
            Equipment.objects.create(recipe=recipe, **equipment)

        tag_objs = []
        for tag in tags_data:
            obj, created = Tag.objects.get_or_create(name=tag['name'])
            tag_objs.append(obj)
        recipe.tags.set(tag_objs)

        for substitute in substitutes_data:
            SubstituteIngredient.objects.create(recipe=recipe, **substitute)

        return recipe


class ProfileImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfileImage
        fields = ['id', 'image_url']

    def get_image_url(self, obj):
        # Return the full URL for the image
        request = self.context.get('request')
        image_url = obj.image.url if obj.image else None
        if image_url:
            return request.build_absolute_uri(image_url)  # Build full URL
        return None


# serializers.py

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser  # or your actual user model
        fields = ['profile_pic']  # include only updatable fields


class MajorIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = MajorIngredient
        fields = ['id', 'name']

class DietaryRestrictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietaryRestriction
        fields = ['id', 'name']

class CuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cuisine
        fields = ['id', 'name']

        
class UserPreferenceSerializer(serializers.ModelSerializer):
    dietary_restrictions = serializers.PrimaryKeyRelatedField(
        queryset=DietaryRestriction.objects.all(), many=True, required=False
    )
    preferred_cuisines = serializers.PrimaryKeyRelatedField(
        queryset=Cuisine.objects.all(), many=True, required=False
    )

    class Meta:
        model = UserPreference
        fields = ['dietary_restrictions', 'preferred_cuisines']




class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ['id', 'user', 'recipe', 'liked_at']
        read_only_fields = ['id', 'user', 'liked_at']