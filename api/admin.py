# Register your models here.
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from .models import (Recipe, Ingredient, Instruction, NutritionalInformation, Equipment,
                      Tag, SubstituteIngredient,CustomUser,SavedRecipe,ProfileImage,
                      UserPreference,DietaryRestriction,Cuisine,MajorIngredient,Course,Like)

class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'cuisine', 'course')

    def save_model(self, request, obj, form, change):
        """Allow only superusers to add recipes."""
        if not request.user.is_superuser:
            raise PermissionDenied("Only superusers can add recipes.")
        super().save_model(request, obj, form, change)

admin.site.register(Recipe, RecipeAdmin)
admin.site.register(Ingredient)
admin.site.register(Instruction)
admin.site.register(NutritionalInformation)
admin.site.register(Equipment)
admin.site.register(Tag)
admin.site.register(SubstituteIngredient)
admin.site.register(CustomUser)
admin.site.register(SavedRecipe)
admin.site.register(ProfileImage)
admin.site.register(DietaryRestriction)
admin.site.register(Cuisine)
admin.site.register(UserPreference)
admin.site.register(MajorIngredient)
admin.site.register(Course)
admin.site.register(Like)