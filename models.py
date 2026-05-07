from django.db import models

class Produto(models.Model):
    nome = models.CharField(max_length=300)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.ForeignKey('Marca', on_delete=models.SET_NULL, null=True, blank=True)
    velocidade = models.CharField(max_length=50, blank=True)
    loja = models.CharField(max_length=100)
    url = models.URLField(unique=True)
    imagem = models.URLField(max_length=500, blank=True, null=True)  # novo campo
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

class Marca(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

class UtilizadorAnonimo(models.Model):
    numero = models.CharField(max_length=12, unique=True)  # ex: ABCD1234EFGH
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.numero

class CarrinhoItem(models.Model):
    utilizador = models.ForeignKey(UtilizadorAnonimo, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    adicionado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('utilizador', 'produto')


