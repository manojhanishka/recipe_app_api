from django.urls import path
from .views import hello_world
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (RegisterUserView,LoginView,UserProfileView,AddRecipeView,GoogleLoginAPIView,
                    save_recipe,remove_saved_recipe,get_saved_recipes,get_all_recipes,VerifyEmailAPIView,
                    get_recipe,check_saved_recipe,get_recommendations,get_similar_recipes,ResendVerificationCodeAPIView,
                    SortedRecipeListView,RecipeFilteredByUserPreferenceView,search_recipes,ProfileImageListView,
                    UserPreferenceListView,FilteredAllRecipeListView,LikedRecipesView,ConfirmResetCodeAPIView,
                    UserPreferenceDeleteView,UserPreferencePartialUpdateView,RecipeSimilarityView,CheckResetCodeAPIView,
                    UpdateRecipeView,AllPreferencesListView,RecipeByMajorIngredientView,FilteredRecipeListView,
                    CuisineListView,CourseListView,DietaryRestrictionListView,RequestPasswordResetAPIView,
                    LogoutView,MajorIngredientListView,LikeRecipeView,UnlikeRecipeView,TagListView)
urlpatterns = [
    path('hello/', hello_world, name='hello'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/request-password-reset/', RequestPasswordResetAPIView.as_view()),
    path('auth/confirm-reset-code/', ConfirmResetCodeAPIView.as_view()),
    path('password/check-code/', CheckResetCodeAPIView.as_view(), name='check-reset-code'),
    path('google-login/', GoogleLoginAPIView.as_view(), name='google-login'),
    path('verify-email/', VerifyEmailAPIView.as_view(), name='verify-email'),
    path('resend-verification-code/', ResendVerificationCodeAPIView.as_view(), name='resend-verification-code'),
    path('register/', RegisterUserView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('filtered-all-recipes/', FilteredAllRecipeListView.as_view(), name='filtered-recipes'),
    path('add-recipe/', AddRecipeView.as_view(), name='add-recipe'),
    path('save-recipe/<int:recipe_id>/', save_recipe, name='save_recipe'),
    path('is_saved/<int:recipe_id>/', check_saved_recipe, name='check_saved_recipe'),
    path('remove-saved-recipe/<int:recipe_id>/', remove_saved_recipe, name='remove_saved_recipe'),
    path('get_saved_recipes/', get_saved_recipes, name='get_saved_recipes'),
    path('all-recipes/', get_all_recipes, name='get-all-recipes'),
    path('recipe/<int:recipe_id>/', get_recipe, name='get-recipe'),
    path('preferences/', UserPreferenceListView.as_view(), name='user-preference-list'),  # GET, POST
    path('preferences/update/', UserPreferencePartialUpdateView.as_view(), name='user-preference-partial-update'),  # PATCH
    path('preferences/delete/', UserPreferenceDeleteView.as_view(), name='user-preference-delete'),  # DELETE
    path('update_recipe/<int:pk>/', UpdateRecipeView.as_view(), name='update-recipe'),
    path('search-recipe/', search_recipes, name='search_recipes'),
    path('profile-images/', ProfileImageListView.as_view(), name='profile_image_list'),
    path('preferences/all/', AllPreferencesListView.as_view(), name='all-preferences'),
    path('major-ingredients/', MajorIngredientListView.as_view(), name='major-ingredient-list'),
    path('recommendations/', get_recommendations, name='get_recommendations'),
    path('recipe_by_major_ings/', RecipeByMajorIngredientView.as_view(), name='recipes-by-major-ingredient'),
    path('like-recipe/', LikeRecipeView.as_view(), name='like-recipe'),
    path('unlike-recipe/', UnlikeRecipeView.as_view(), name='unlike-recipe'),
    path('similar-recipes/<int:recipe_id>/', get_similar_recipes, name='get-similar-recipes'),
    path('liked-recipes/', LikedRecipesView.as_view(), name='liked-recipes'),
    path('recipes/sorted/', SortedRecipeListView.as_view(), name='sorted-recipe-list'),
    path('filter-by-preference/', RecipeFilteredByUserPreferenceView.as_view(), name='filter-by-preference'),
    path('generate-recipe/', RecipeSimilarityView.as_view(), name='recipe-similarity'),
    path('cuisines/', CuisineListView.as_view(), name='cuisine-list'),
    path('courses/', CourseListView.as_view(), name='course-list'),
    path('tags/', TagListView.as_view(), name='tag-list'),
    path('apply-filters/', FilteredRecipeListView.as_view(), name='filtered-recipes'),

    path('dietary-restrictions/', DietaryRestrictionListView.as_view(), name='dietary-restriction-list'),
    path('logout/', LogoutView.as_view(), name='logout'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)