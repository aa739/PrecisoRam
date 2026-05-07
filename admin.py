# Register your models here.
# precisoram/admin.py
from django.contrib import admin
from .models import Produto, Marca, UtilizadorAnonimo, CarrinhoItem

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'marca', 'velocidade', 'loja', 'ultima_atualizacao')
    list_filter = ('loja', 'marca', 'velocidade')
    search_fields = ('nome', 'marca__nome')
    ordering = ('-ultima_atualizacao',)

@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(UtilizadorAnonimo)
class UtilizadorAnonimoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'criado_em')
    search_fields = ('numero',)
    readonly_fields = ('numero', 'criado_em')

@admin.register(CarrinhoItem)
class CarrinhoItemAdmin(admin.ModelAdmin):
    list_display = ('utilizador', 'produto', 'quantidade', 'adicionado_em')
    list_filter = ('adicionado_em',)
