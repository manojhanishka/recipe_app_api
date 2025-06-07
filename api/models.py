
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from cloudinary.models import CloudinaryField

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, phone, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        if not username:
            raise ValueError("Username is required")
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, phone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, phone, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    reset_code = models.CharField(max_length=6, blank=True, null=True)
    profile_pic = CloudinaryField('image', blank=True, null=True)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'phone']

    def __str__(self):
        return self.username
    


class MajorIngredient(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
    
class DietaryRestriction(models.Model):
    name = models.CharField(max_length=100,null=True)

    def __str__(self):
        return self.name



class Cuisine(models.Model):
    name = models.CharField(max_length=100,null=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Tag(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name



class Recipe(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    preparation_time = models.CharField(max_length=50)
    cooking_time = models.CharField(max_length=50)
    total_time = models.CharField(max_length=50)
    servings = models.CharField(max_length=50)
    difficulty_level = models.CharField(max_length=50)
    cuisine = models.ForeignKey(Cuisine, on_delete=models.SET_NULL, null=True, related_name="recipes")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, related_name="recipes")
    dietary_restrictions = models.ManyToManyField(DietaryRestriction, blank=True, related_name="recipes")
    ingredients_notes = models.TextField(blank=True, null=True)
    cooking_tips = models.TextField(blank=True, null=True)
    image = CloudinaryField('image', blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, related_name='recipes')
    major_ingredients = models.ManyToManyField(MajorIngredient, related_name="recipes", blank=True)
    
    def like_count(self):
        return self.likes.count()

    def is_liked_by_user(self, user):
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False

    def __str__(self):
        return self.title

class Ingredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="ingredients", on_delete=models.CASCADE)
    ingredient = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.ingredient} - {self.quantity}"

class Instruction(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="instructions", on_delete=models.CASCADE)
    step = models.TextField()

    def __str__(self):
        return self.step[:50]  # Show only the first 50 characters

class NutritionalInformation(models.Model):
    recipe = models.OneToOneField(Recipe, related_name="nutritional_information", on_delete=models.CASCADE)
    calories = models.CharField(max_length=50)
    protein = models.CharField(max_length=50)
    carbs = models.CharField(max_length=50)
    fat = models.CharField(max_length=50)

    def __str__(self):
        return f"Calories: {self.calories}, Protein: {self.protein}"

class Equipment(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="equipment", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SubstituteIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, related_name="substitutes", on_delete=models.CASCADE)
    ingredient = models.CharField(max_length=100)
    substitute = models.CharField(max_length=100)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.ingredient} -> {self.substitute}"





class Like(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='likes')
    recipe = models.ForeignKey('Recipe', on_delete=models.CASCADE, related_name='likes')
    liked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')  # Prevent duplicate likes

    def __str__(self):
        return f"{self.user.username} liked {self.recipe.title}"
    


class UserPreference(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='preferences', on_delete=models.CASCADE)
    
    dietary_restrictions = models.ManyToManyField(DietaryRestriction, blank=True)
    preferred_cuisines = models.ManyToManyField(Cuisine, blank=True)
    
    def __str__(self):
        return f"Preferences for {self.user.username}"

class SavedRecipe(models.Model):
    user = models.ForeignKey(CustomUser, related_name="saved_recipes", on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, related_name="saved_by_users", on_delete=models.CASCADE)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'recipe')  # Ensures a user can't save the same recipe multiple times

    def __str__(self):
        return f"{self.user.username} saved {self.recipe.title}"



class ProfileImage(models.Model):
    image = models.ImageField(upload_to='profile_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
