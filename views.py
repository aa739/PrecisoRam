import random
import string
import csv
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from .models import Produto, Marca, UtilizadorAnonimo, CarrinhoItem
from .scraping import atualizar_produtos

# ---------- Funções auxiliares ----------
def gerar_numero_mullvad():
    parte1 = ''.join(random.choices(string.ascii_uppercase, k=4))
    parte2 = ''.join(random.choices(string.digits, k=4))
    parte3 = ''.join(random.choices(string.ascii_uppercase, k=4))
    return f"{parte1}{parte2}{parte3}"

def obter_utilizador_sessao(request):
    numero = request.session.get('numero_utilizador')
    if numero:
        try:
            return UtilizadorAnonimo.objects.get(numero=numero)
        except UtilizadorAnonimo.DoesNotExist:
            del request.session['numero_utilizador']
    return None

def lista_produtos(request):
    produtos = Produto.objects.all()

    # ---- Filtros ----
    min_preco = request.GET.get('min_preco')
    max_preco = request.GET.get('max_preco')
    velocidade = request.GET.get('velocidade')
    marca_id = request.GET.get('marca')
    
    if min_preco:
        produtos = produtos.filter(preco__gte=float(min_preco))
    if max_preco:
        produtos = produtos.filter(preco__lte=float(max_preco))
    if velocidade:
        produtos = produtos.filter(velocidade=velocidade)
    if marca_id:
        produtos = produtos.filter(marca_id=int(marca_id))

    # ---- Ordenação ----
    order = request.GET.get('order')
    if order == 'asc':
        produtos = produtos.order_by('preco')
    elif order == 'desc':
        produtos = produtos.order_by('-preco')
    else:
        produtos = produtos.order_by('nome')  # padrão

    # ---- Contexto para o template (manter valores dos filtros) ----
    marcas = Marca.objects.all()
    velocidades = Produto.objects.exclude(velocidade='').values_list('velocidade', flat=True).distinct()
    is_admin = request.user.is_authenticated and request.user.is_staff

    context = {
        'produtos': produtos,
        'marcas': marcas,
        'velocidades': velocidades,
        'is_admin': is_admin,
        # valores atuais dos filtros
        'min_preco': min_preco,
        'max_preco': max_preco,
        'velocidade_selecionada': velocidade,
        'marca_selecionada': marca_id,
        'order_selecionado': order,
    }
    return render(request, 'precisoram/lista_produtos.html', context)

def scraping_view(request):
    if request.method == 'POST' or True: 
        atualizar_produtos()
        messages.success(request, "Base de dados atualizada com scraping.")
    return redirect('lista_produtos')

def adicionar_carrinho(request, produto_id):
    """Adiciona produto ao carrinho — sessão para anónimos, BD para utilizadores logados."""
    get_object_or_404(Produto, id=produto_id)
    produto = Produto.objects.get(id=produto_id)
    
    user = obter_utilizador_sessao(request)
    
    if user:
        # Utilizador logado — guarda na BD
        item, created = CarrinhoItem.objects.get_or_create(utilizador=user, produto=produto)
        if not created:
            item.quantidade += 1
            item.save()
    else:
        # Anónimo — guarda na sessão
        carrinho = request.session.get('carrinho', {})
        chave = str(produto_id)
        carrinho[chave] = carrinho.get(chave, 0) + 1
        request.session['carrinho'] = carrinho
        request.session.modified = True
    
    messages.success(request, f"{produto.nome} adicionado ao carrinho.")
    
    # Preserva filtros
    params = request.GET.copy()
    params['adicionado'] = produto_id
    return redirect(f"{reverse('lista_produtos')}?{params.urlencode()}")


def ver_carrinho(request):
    """Mostra carrinho — da BD para utilizadores logados, da sessão para anónimos."""
    user = obter_utilizador_sessao(request)
    itens = []
    total = 0
    
    if user:
        # Utilizador logado — lê da BD
        carrinho_items = CarrinhoItem.objects.filter(utilizador=user).select_related('produto')
        for item in carrinho_items:
            subtotal = item.produto.preco * item.quantidade
            total += subtotal
            itens.append({
                'produto': item.produto,
                'quantidade': item.quantidade,
                'subtotal': subtotal,
            })
    else:
        # Anónimo — lê da sessão
        carrinho = request.session.get('carrinho', {})
        for produto_id, quantidade in carrinho.items():
            try:
                produto = Produto.objects.get(id=int(produto_id))
                subtotal = produto.preco * quantidade
                total += subtotal
                itens.append({
                    'produto': produto,
                    'quantidade': quantidade,
                    'subtotal': subtotal,
                })
            except Produto.DoesNotExist:
                pass
    
    return render(request, 'precisoram/carrinho.html', {'itens': itens, 'total': total})


def remover_do_carrinho(request, produto_id):
    """Remove produto do carrinho — da BD ou da sessão conforme o caso."""
    user = obter_utilizador_sessao(request)
    
    if user:
        # Utilizador logado — remove da BD
        try:
            item = CarrinhoItem.objects.get(utilizador=user, produto_id=produto_id)
            item.delete()
            messages.warning(request, "Produto removido do carrinho.")
        except CarrinhoItem.DoesNotExist:
            messages.warning(request, "Produto não encontrado.")
    else:
        # Anónimo — remove da sessão
        carrinho = request.session.get('carrinho', {})
        chave = str(produto_id)
        if chave in carrinho:
            del carrinho[chave]
            request.session['carrinho'] = carrinho
            request.session.modified = True
            messages.warning(request, "Produto removido do carrinho.")
        else:
            messages.warning(request, "Produto não encontrado.")
    
    return redirect('ver_carrinho')


def remover_tudo_carrinho(request):
    """Esvazia o carrinho — da BD ou da sessão."""
    user = obter_utilizador_sessao(request)
    
    if user:
        CarrinhoItem.objects.filter(utilizador=user).delete()
    else:
        request.session['carrinho'] = {}
        request.session.modified = True
    
    messages.warning(request, "Carrinho esvaziado completamente.")
    return redirect('ver_carrinho')


def exportar_csv(request):
    """Exporta carrinho para CSV — da BD ou da sessão."""
    user = obter_utilizador_sessao(request)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="carrinho_precisoram.csv"'
    writer = csv.writer(response)
    writer.writerow(['Produto', 'Preço (€)', 'Quantidade', 'Subtotal (€)', 'Loja', 'URL'])
    
    total = 0
    
    if user:
        # Utilizador logado — exporta da BD
        carrinho_items = CarrinhoItem.objects.filter(utilizador=user).select_related('produto')
        if not carrinho_items:
            messages.warning(request, "Carrinho vazio.")
            return redirect('ver_carrinho')
        
        for item in carrinho_items:
            subtotal = item.produto.preco * item.quantidade
            total += subtotal
            writer.writerow([
                item.produto.nome,
                item.produto.preco,
                item.quantidade,
                subtotal,
                item.produto.loja,
                item.produto.url
            ])
    else:
        # Anónimo — exporta da sessão
        carrinho = request.session.get('carrinho', {})
        if not carrinho:
            messages.warning(request, "Carrinho vazio.")
            return redirect('ver_carrinho')
        
        for produto_id, quantidade in carrinho.items():
            try:
                produto = Produto.objects.get(id=int(produto_id))
                subtotal = produto.preco * quantidade
                total += subtotal
                writer.writerow([produto.nome, produto.preco, quantidade, subtotal, produto.loja, produto.url])
            except Produto.DoesNotExist:
                pass
    
    writer.writerow([])
    writer.writerow(['TOTAL GERAL', '', '', total, '', ''])
    return response


def login_mullvad(request):
    if request.method == 'POST':
        numero = request.POST.get('numero', '').strip().upper()
        if numero:
            try:
                user = UtilizadorAnonimo.objects.get(numero=numero)
                request.session['numero_utilizador'] = user.numero
                # NÃO limpa o carrinho — mantém os items da BD do utilizador
                messages.success(request, f"Bem-vindo, {user.numero}!")
                return redirect('lista_produtos')
            except UtilizadorAnonimo.DoesNotExist:
                messages.error(request, "Número inválido.")
        else:
            messages.error(request, "Introduza um número.")
    return render(request, 'precisoram/login.html')


def registar_mullvad(request):
    novo_numero = None
    if request.method == 'POST':
        novo_numero = gerar_numero_mullvad()
        while UtilizadorAnonimo.objects.filter(numero=novo_numero).exists():
            novo_numero = gerar_numero_mullvad()
        user = UtilizadorAnonimo.objects.create(numero=novo_numero)
        request.session['numero_utilizador'] = user.numero
        # Carrinho novo vazio (não há items na BD para novo utilizador)
        return render(request, 'precisoram/registar.html', {'novo_numero': novo_numero})
    return render(request, 'precisoram/registar.html', {'novo_numero': None})


def logout_mullvad(request):
    if 'numero_utilizador' in request.session:
        del request.session['numero_utilizador']
    # NÃO limpa carrinho — os items ficam guardados na BD do utilizador
    messages.info(request, "Sessão terminada.")
    return redirect('lista_produtos')
