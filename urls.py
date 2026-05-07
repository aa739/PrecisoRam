from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_produtos, name='lista_produtos'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('adicionar/<int:produto_id>/', views.adicionar_carrinho, name='adicionar_carrinho'),
    path('remover/<int:produto_id>/', views.remover_do_carrinho, name='remover_do_carrinho'),
    path('remover_tudo/', views.remover_tudo_carrinho, name='remover_tudo_carrinho'),
    path('exportar/', views.exportar_csv, name='exportar_csv'),
    path('scraping/', views.scraping_view, name='scraping'),
    path('login/', views.login_mullvad, name='login_mullvad'),
    path('registar/', views.registar_mullvad, name='registar_mullvad'),
    path('logout/', views.logout_mullvad, name='logout_mullvad'),
]
