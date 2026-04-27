import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import aiohttp

# ========= CONFIGURAÇÕES =========
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    print("Configure a variável de ambiente DISCORD_TOKEN no Railway")
    sys.exit(1)

# ========= ID DOS CANAIS E CATEGORIAS =========
CARGO_ADMIN_ID = int(os.getenv("CARGO_ADMIN_ID", "1498104494226014319"))
CATEGORIA_FARMS_ID = int(os.getenv("CATEGORIA_FARMS_ID", "1498108914703532183"))
CATEGORIA_PAINEL_ID = int(os.getenv("CATEGORIA_PAINEL_ID", "1498111045489790987"))
CHAT_LOGS_ID = int(os.getenv("CHAT_LOGS_ID", "1498109309622550638"))
CHAT_ADMIN_LOGS_ID = int(os.getenv("CHAT_ADMIN_LOGS_ID", "1498109569853816963"))
CHAT_RANK_ID = int(os.getenv("CHAT_RANK_ID", "1498109956421976124"))
CHAT_COMPRA_VENDA_ID = int(os.getenv("CHAT_COMPRA_VENDA_ID", "1498110154317496330"))

# ========= BANCO DE DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "admins": [],
    "config": {},
    "caixa_semana": {},
    "compras_vendas": []
}

# ========= FUNÇÕES AUXILIARES =========
def salvar_dados():
    try:
        with open("dados_bot.json", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print("Dados salvos")
    except Exception as e:
        print(f"Erro ao salvar: {e}")

def carregar_dados():
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            dados.update(json.load(f))
        print("Dados carregados")
        return True
    except:
        print("Novo banco de dados")
        return False

# ========= FUNÇÕES PARA ENVIAR LOGS =========
async def log_acao(acao, usuario, detalhes, cor=None):
    """Envia log para o canal de logs"""
    cores = {
        "criar_canal": 0x00ff00,
        "registrar_farm": 0x00ff00,
        "pagar": 0xffa500,
        "fechar_canal": 0xff0000,
        "fechar_caixa": 0xffa500,
        "reset_rank": 0xff0000,
        "erro": 0xff0000,
        "info": 0x3498db,
        "admin": 0x9b59b6,
        "setar_admin": 0x9b59b6,
        "compra_venda": 0x00ff00
    }
    
    cor_final = cores.get(acao, 0x3498db) if cor is None else cor
    
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs and isinstance(canal_logs, discord.TextChannel):
        embed = discord.Embed(
            title=f"LOG: {acao.upper()}",
            description=detalhes,
            color=cor_final,
            timestamp=datetime.now()
        )
        if usuario:
            embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        else:
            embed.set_author(name="Sistema")
        embed.set_footer(text=f"Sistema de Farm • {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        await canal_logs.send(embed=embed)

async def log_admin(titulo, descricao, cor=0xffa500):
    """Envia log para o canal de admin logs"""
    canal_admin = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal_admin and isinstance(canal_admin, discord.TextChannel):
        embed = discord.Embed(
            title=titulo,
            description=descricao,
            color=cor,
            timestamp=datetime.now()
        )
        await canal_admin.send(embed=embed)

async def log_criar_canal(usuario, canal):
    """Log específico para criação de canal"""
    canal_admin = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal_admin and isinstance(canal_admin, discord.TextChannel):
        embed = discord.Embed(
            title="NOVO CANAL PRIVADO",
            description=f"**Usuário:** {usuario.mention}\n**Canal:** {canal.mention}\n**ID:** {canal.id}",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        await canal_admin.send(embed=embed)

# ========= BOT PRINCIPAL =========
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# ========= FUNÇÃO PARA VERIFICAR SE É ADMIN =========
def is_admin(member) -> bool:
    if not hasattr(member, 'guild'):
        return False
    
    cargo_admin = member.guild.get_role(CARGO_ADMIN_ID)
    if cargo_admin and cargo_admin in member.roles:
        return True
    
    if str(member.id) in dados["admins"]:
        return True
    
    if hasattr(member, 'guild_permissions') and member.guild_permissions.administrator:
        return True
    
    return False

# ========= FUNÇÕES PARA RANKING =========
async def resetar_ranking(interaction: discord.Interaction = None):
    """Reseta todo o ranking (apenas admin)"""
    if interaction and not is_admin(interaction.user):
        await interaction.response.send_message("Apenas administradores podem resetar o ranking!", ephemeral=True)
        return False
    
    # Salvar backup antes de resetar
    backup = {
        "usuarios": dados["usuarios"].copy(),
        "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin": interaction.user.name if interaction else "Sistema"
    }
    
    # Salvar backup em arquivo
    with open(f"backup_rank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    
    # Resetar dados do ranking (manter admins e configurações)
    dados["usuarios"] = {}
    dados["caixa_semana"] = {}
    salvar_dados()
    
    # Registrar log
    await log_acao(
        "reset_rank",
        interaction.user if interaction else None,
        f"Ranking foi resetado por {interaction.user.mention if interaction else 'Sistema'}\nBackup salvo.",
        0xff0000
    )
    
    await log_admin(
        "RANKING RESETADO",
        f"**Admin:** {interaction.user.mention if interaction else 'Sistema'}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}\n**Backup salvo**",
        0xff0000
    )
    
    return True

async def atualizar_ranking():
    """Atualiza o canal de ranking com todas as categorias"""
    canal_rank = bot.get_channel(CHAT_RANK_ID)
    if not canal_rank:
        print(f"Canal de rank {CHAT_RANK_ID} não encontrado!")
        return
    
    if not isinstance(canal_rank, discord.TextChannel):
        print(f"Canal {CHAT_RANK_ID} não é um canal de texto!")
        return
    
    async for msg in canal_rank.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()
    
    usuarios_data = []
    for user_id, data in dados["usuarios"].items():
        try:
            user = await bot.fetch_user(int(user_id))
            total_farms = sum(f["quantidade"] for f in data["farms"])
            total_pagamentos = sum(p["valor"] for p in data["pagamentos"])
            dinheiro_sujo = total_farms - total_pagamentos
            
            usuarios_data.append({
                "nome": user.name,
                "user_id": user_id,
                "total_farms": total_farms,
                "total_pagamentos": total_pagamentos,
                "dinheiro_sujo": max(0, dinheiro_sujo)
            })
        except:
            continue
    
    ranking_farms = sorted(usuarios_data, key=lambda x: x["total_farms"], reverse=True)[:10]
    ranking_dinheiro_sujo = sorted(usuarios_data, key=lambda x: x["dinheiro_sujo"], reverse=True)[:10]
    ranking_pagamentos = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:10]
    
    embed = discord.Embed(
        title="RANKING GERAL",
        description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        color=discord.Color.gold()
    )
    
    ranking_text = ""
    for i, u in enumerate(ranking_farms, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        ranking_text += f"{medalha} **{u['nome']}** - {u['total_farms']:,} itens\n"
    embed.add_field(name="META FARM", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_dinheiro_sujo, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        ranking_text += f"{medalha} **{u['nome']}** - R$ {u['dinheiro_sujo']:,}\n"
    embed.add_field(name="DINHEIRO SUJO", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_pagamentos, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        ranking_text += f"{medalha} **{u['nome']}** - R$ {u['total_pagamentos']:,}\n"
    embed.add_field(name="TOP MONEY", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    embed.set_footer(text="Use os botões abaixo para gerenciar o ranking")
    
    view = RankingView()
    await canal_rank.send(embed=embed, view=view)

class RankingView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.primary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await atualizar_ranking()
        await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        # Verificar se é admin
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem resetar o ranking!", ephemeral=True)
            return
        
        # Criar view de confirmação
        view = ConfirmarResetView()
        await interaction.response.send_message(
            "⚠️ **ATENÇÃO!** ⚠️\n\n"
            "Você tem certeza que deseja RESETAR TODO O RANKING?\n\n"
            "Isso irá:\n"
            "• Apagar todas as farms registradas\n"
            "• Apagar todos os pagamentos\n"
            "• Apagar todo o histórico de caixa\n\n"
            "**Um backup será salvo automaticamente antes do reset.**\n\n"
            "Esta ação é IRREVERSÍVEL!",
            view=view,
            ephemeral=True
        )

class ConfirmarResetView(View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        # Resetar ranking
        sucesso = await resetar_ranking(interaction)
        
        if sucesso:
            await interaction.followup.send("✅ Ranking resetado com sucesso! Um backup foi salvo.", ephemeral=True)
            # Atualizar o ranking para mostrar vazio
            await atualizar_ranking()
        else:
            await interaction.followup.send("❌ Erro ao resetar ranking.", ephemeral=True)
        
        self.stop()
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

# ========= MODAL PARA REGISTRAR MÚLTIPLOS PRODUTOS =========
class FarmModal(Modal, title="Registrar Nova Farm"):
    chumbo = TextInput(
        label="CHUMBO - Quantidade",
        placeholder="Ex: 250 (deixe em branco se não tiver)",
        required=False,
        style=discord.TextStyle.short
    )
    capsula = TextInput(
        label="CAPSULA - Quantidade",
        placeholder="Ex: 150 (deixe em branco se não tiver)",
        required=False,
        style=discord.TextStyle.short
    )
    polvora = TextInput(
        label="POLVORA - Quantidade",
        placeholder="Ex: 300 (deixe em branco se não tiver)",
        required=False,
        style=discord.TextStyle.short
    )
    
    def __init__(self, user_id, imagem_url, user_name, canal_nome):
        super().__init__()
        self.user_id = user_id
        self.imagem_url = imagem_url
        self.user_name = user_name
        self.canal_nome = canal_nome
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        produtos_registrados = []
        
        if self.chumbo.value and self.chumbo.value.strip():
            try:
                qtd = int(self.chumbo.value.strip())
                if qtd > 0:
                    produtos_registrados.append({"produto": "CHUMBO", "quantidade": qtd})
            except ValueError:
                pass
        
        if self.capsula.value and self.capsula.value.strip():
            try:
                qtd = int(self.capsula.value.strip())
                if qtd > 0:
                    produtos_registrados.append({"produto": "CAPSULA", "quantidade": qtd})
            except ValueError:
                pass
        
        if self.polvora.value and self.polvora.value.strip():
            try:
                qtd = int(self.polvora.value.strip())
                if qtd > 0:
                    produtos_registrados.append({"produto": "POLVORA", "quantidade": qtd})
            except ValueError:
                pass
        
        if not produtos_registrados:
            await interaction.followup.send("Nenhum produto válido! Preencha pelo menos um produto com quantidade válida.", ephemeral=True)
            return
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name}
        
        registros = []
        for produto in produtos_registrados:
            farm_registro = {
                "produto": produto["produto"],
                "quantidade": produto["quantidade"],
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "print_url": self.imagem_url,
                "validado": True
            }
            dados["usuarios"][str(self.user_id)]["farms"].append(farm_registro)
            registros.append(farm_registro)
        
        salvar_dados()
        
        embed = discord.Embed(
            title="FARMS REGISTRADAS COM SUCESSO",
            color=discord.Color.green()
        )
        
        descricao = ""
        for reg in registros:
            descricao += f"**{reg['produto']}:** {reg['quantidade']} itens\n"
        
        embed.description = descricao
        embed.add_field(name="Data do registro", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms registradas", inline=False)
        embed.set_image(url=self.imagem_url)
        embed.set_footer(text="Obrigado por registrar suas farms!")
        
        total_itens = sum(reg["quantidade"] for reg in registros)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        produtos_str = ", ".join([f"{p['produto']}: {p['quantidade']}" for p in registros])
        await log_acao(
            "registrar_farm",
            interaction.user,
            f"**Canal:** {self.canal_nome}\n**Produtos:** {produtos_str}\n**Total de itens:** {total_itens}"
        )
        
        await log_admin(
            "NOVA FARM REGISTRADA",
            f"**Usuário:** {interaction.user.mention}\n**Canal:** {self.canal_nome}\n**Produtos:**\n{produtos_str}\n**Total de itens:** {total_itens}",
            0x00ff00
        )
        
        await atualizar_ranking()

# ========= MODAL PARA FECHAMENTO DE CAIXA =========
class FechamentoCaixaModal(Modal, title="Fechamento de Caixa da Semana"):
    meta_farm = TextInput(
        label="Meta de Farm",
        placeholder="Ex: 5000",
        required=True,
        style=discord.TextStyle.short
    )
    farm_sujo = TextInput(
        label="Farm Sujo",
        placeholder="Ex: 3500",
        required=True,
        style=discord.TextStyle.short
    )
    salario = TextInput(
        label="Salário",
        placeholder="Ex: 1000",
        required=True,
        style=discord.TextStyle.short
    )
    extra = TextInput(
        label="Extra",
        placeholder="Ex: 200",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem fechar caixa!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            meta = float(self.meta_farm.value.replace(",", "."))
            sujo = float(self.farm_sujo.value.replace(",", "."))
            salario_valor = float(self.salario.value.replace(",", "."))
            extra_valor = float(self.extra.value.replace(",", "."))
            total = meta + sujo + salario_valor + extra_valor
        except ValueError:
            await interaction.followup.send("Valores inválidos! Use apenas números.", ephemeral=True)
            return
        
        valor_pagamento = salario_valor + extra_valor
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name}
        
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor_pagamento,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id,
            "admin_nome": interaction.user.name,
            "tipo": "Fechamento de Caixa Semanal",
            "salario": salario_valor,
            "extra": extra_valor
        })
        
        fechamento = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name,
            "admin_id": interaction.user.id,
            "usuario": self.user_name,
            "usuario_id": self.user_id,
            "meta_farm": meta,
            "farm_sujo": sujo,
            "salario": salario_valor,
            "extra": extra_valor,
            "total": total,
            "valor_pago": valor_pagamento
        }
        
        if str(self.user_id) not in dados["caixa_semana"]:
            dados["caixa_semana"][str(self.user_id)] = []
        
        dados["caixa_semana"][str(self.user_id)].append(fechamento)
        salvar_dados()
        
        lucro_liquido = total - salario_valor - extra_valor
        
        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            embed_notificacao = discord.Embed(
                title="PAGAMENTO RECEBIDO",
                description=f"Você recebeu um pagamento referente ao fechamento de caixa!",
                color=discord.Color.green()
            )
            embed_notificacao.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
            embed_notificacao.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
            embed_notificacao.add_field(name="Total Recebido", value=f"R$ {valor_pagamento:,.2f}", inline=True)
            embed_notificacao.add_field(name="Admin Responsável", value=interaction.user.mention, inline=True)
            embed_notificacao.set_footer(text="Fechamento de caixa semanal")
            await user.send(embed=embed_notificacao)
        except:
            pass
        
        embed = discord.Embed(
            title="FECHAMENTO DE CAIXA SEMANAL",
            description=f"**{self.user_name}**, seu fechamento foi registrado!",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Meta de Farm", value=f"R$ {meta:,.2f}", inline=True)
        embed.add_field(name="Farm Sujo", value=f"R$ {sujo:,.2f}", inline=True)
        embed.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
        embed.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
        embed.add_field(name="TOTAL BRUTO", value=f"R$ {total:,.2f}", inline=True)
        embed.add_field(name="PAGAMENTO REALIZADO", value=f"R$ {valor_pagamento:,.2f}", inline=True)
        embed.add_field(name="Lucro Líquido", value=f"R$ {lucro_liquido:,.2f}", inline=True)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        embed.set_footer(text="Caixa semanal fechado com sucesso!")
        
        if lucro_liquido < 0:
            embed.color = discord.Color.red()
        elif lucro_liquido > 5000:
            embed.color = discord.Color.green()
        
        await self.canal.send(embed=embed)
        await interaction.followup.send(
            f"Fechamento de caixa registrado!\n\n"
            f"Resumo:\n"
            f"Meta Farm: R$ {meta:,.2f}\n"
            f"Farm Sujo: R$ {sujo:,.2f}\n"
            f"Salário: R$ {salario_valor:,.2f}\n"
            f"Extra: R$ {extra_valor:,.2f}\n"
            f"Total do Caixa: R$ {total:,.2f}\n"
            f"Pagamento Realizado: R$ {valor_pagamento:,.2f}",
            ephemeral=True
        )
        
        await log_acao(
            "fechar_caixa",
            interaction.user,
            f"**Usuário:** {self.user_name}\n"
            f"**Meta Farm:** R$ {meta}\n"
            f"**Farm Sujo:** R$ {sujo}\n"
            f"**Salário:** R$ {salario_valor}\n"
            f"**Extra:** R$ {extra_valor}\n"
            f"**Total:** R$ {total}\n"
            f"**Pagamento:** R$ {valor_pagamento}",
            0xffa500
        )
        
        await log_admin(
            "FECHAMENTO DE CAIXA",
            f"**Usuário:** {self.user_name}\n"
            f"**Admin:** {interaction.user.mention}\n"
            f"**Salário:** R$ {salario_valor:,.2f}\n"
            f"**Extra:** R$ {extra_valor:,.2f}\n"
            f"**Total Pago:** R$ {valor_pagamento:,.2f}",
            0xffa500
        )
        
        await atualizar_ranking()

# ========= MODAIS PARA COMPRA E VENDA =========
class VendaModal(Modal, title="Venda de Munição"):
    quantidade = TextInput(
        label="Quantidade",
        placeholder="Ex: 1000",
        required=True,
        style=discord.TextStyle.short
    )
    valor_total = TextInput(
        label="Valor Total (R$)",
        placeholder="Ex: 500",
        required=True,
        style=discord.TextStyle.short
    )
    faccao_compradora = TextInput(
        label="Facção Compradora",
        placeholder="Ex: Primeiro Comando, Família do Norte, etc",
        required=True,
        style=discord.TextStyle.short
    )
    responsavel = TextInput(
        label="Responsável pela Venda",
        placeholder="Ex: @usuario ou nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True)
            return
        
        faccao = self.faccao_compradora.value.strip()
        responsavel_nome = self.responsavel.value.strip()
        
        embed = discord.Embed(
            title="VENDA DE MUNIÇÃO",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Quantidade", value=f"{qtd:,} munições", inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Facção Compradora", value=faccao, inline=True)
        embed.add_field(name="Responsável", value=responsavel_nome, inline=True)
        embed.add_field(name="Registrado por", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Venda registrada com sucesso!")
        
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas and isinstance(canal_vendas, discord.TextChannel):
            await canal_vendas.send(embed=embed)
            
            dados["compras_vendas"].append({
                "tipo": "venda",
                "quantidade": qtd,
                "valor_total": valor,
                "faccao_compradora": faccao,
                "responsavel": responsavel_nome,
                "registrado_por": interaction.user.id,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            salvar_dados()
            await interaction.followup.send("Venda registrada com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("Canal de vendas não encontrado! Contate um administrador.", ephemeral=True)
        
        await log_acao(
            "compra_venda",
            interaction.user,
            f"**Venda:** {qtd} munições por R$ {valor}\n**Facção Compradora:** {faccao}\n**Responsável:** {responsavel_nome}",
            0x00ff00
        )

class CompraModal(Modal, title="Compra de Produto"):
    quantidade = TextInput(
        label="Quantidade",
        placeholder="Ex: 1000",
        required=True,
        style=discord.TextStyle.short
    )
    produto = TextInput(
        label="Produto",
        placeholder="Ex: Munição, Kit, Arma etc",
        required=True,
        style=discord.TextStyle.short
    )
    valor_total = TextInput(
        label="Valor Total (R$)",
        placeholder="Ex: 500",
        required=True,
        style=discord.TextStyle.short
    )
    faccao_vendedora = TextInput(
        label="Facção Vendedora",
        placeholder="Ex: Primeiro Comando, Família do Norte, etc",
        required=True,
        style=discord.TextStyle.short
    )
    responsavel = TextInput(
        label="Responsável pela Compra",
        placeholder="Ex: @usuario ou nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            qtd = int(self.quantidade.value)
            valor = float(self.valor_total.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True)
            return
        
        produto_nome = self.produto.value
        faccao = self.faccao_vendedora.value.strip()
        responsavel_nome = self.responsavel.value.strip()
        
        embed = discord.Embed(
            title="COMPRA DE PRODUTO",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Quantidade", value=f"{qtd:,}", inline=True)
        embed.add_field(name="Produto", value=produto_nome, inline=True)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}", inline=True)
        embed.add_field(name="Facção Vendedora", value=faccao, inline=True)
        embed.add_field(name="Responsável", value=responsavel_nome, inline=True)
        embed.add_field(name="Registrado por", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Compra registrada com sucesso!")
        
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas and isinstance(canal_vendas, discord.TextChannel):
            await canal_vendas.send(embed=embed)
            
            dados["compras_vendas"].append({
                "tipo": "compra",
                "quantidade": qtd,
                "produto": produto_nome,
                "valor_total": valor,
                "faccao_vendedora": faccao,
                "responsavel": responsavel_nome,
                "registrado_por": interaction.user.id,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            salvar_dados()
            await interaction.followup.send("Compra registrada com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("Canal de vendas não encontrado! Contate um administrador.", ephemeral=True)
        
        await log_acao(
            "compra_venda",
            interaction.user,
            f"**Compra:** {qtd} x {produto_nome} por R$ {valor}\n**Facção Vendedora:** {faccao}\n**Responsável:** {responsavel_nome}",
            0x00ff00
        )

class CompraVendaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Venda de Munição", style=discord.ButtonStyle.success, emoji="💸")
    async def venda(self, interaction: discord.Interaction, button: Button):
        modal = VendaModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Compra de Produto", style=discord.ButtonStyle.primary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button):
        modal = CompraModal()
        await interaction.response.send_modal(modal)

# ========= MODAL PARA MUDAR NOME DO CANAL =========
class MudarNomeModal(Modal, title="Mudar Nome do Canal"):
    novo_nome = TextInput(
        label="Novo nome do canal",
        placeholder="Ex: farm-lucas, farm-joao, farm-equipe",
        required=True,
        style=discord.TextStyle.short,
        max_length=90
    )
    
    def __init__(self, canal_atual):
        super().__init__()
        self.canal_atual = canal_atual
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem mudar o nome do canal!", ephemeral=True)
            return
        
        nome_antigo = self.canal_atual.name
        novo_nome = self.novo_nome.value.lower().replace(" ", "-")
        novo_nome = ''.join(c for c in novo_nome if c.isalnum() or c == '-')
        
        if not novo_nome:
            novo_nome = "farm"
        
        try:
            await self.canal_atual.edit(name=novo_nome)
            await interaction.response.send_message(f"Nome do canal alterado para: `{novo_nome}`", ephemeral=True)
            
            await log_acao(
                "info",
                interaction.user,
                f"**Canal renomeado:**\nAntigo: `{nome_antigo}`\nNovo: `{novo_nome}`",
                0x3498db
            )
            
            await log_admin(
                "CANAL RENOMEADO",
                f"**Admin:** {interaction.user.mention}\n**Canal:** {self.canal_atual.mention}\n**Nome antigo:** `{nome_antigo}`\n**Novo nome:** `{novo_nome}`",
                0x3498db
            )
        except Exception as e:
            await interaction.response.send_message(f"Erro ao alterar nome: {str(e)[:100]}", ephemeral=True)

# ========= VIEW DO CANAL PRIVADO =========
class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id
    
    @discord.ui.button(label="Nova Farm", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def nova_farm(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Este canal é privado! Apenas o dono e administradores podem usar.", ephemeral=True)
            return
        
        imagem_url = None
        async for msg in interaction.channel.history(limit=20):
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        imagem_url = attachment.url
                        break
                if imagem_url:
                    break
        
        if not imagem_url:
            await interaction.response.send_message(
                "Nenhuma print encontrada!\n\n"
                "Como registrar:\n"
                "1️⃣ Anexe a print da farm (botão 📎)\n"
                "2️⃣ Clique novamente em Nova Farm\n"
                "3️⃣ Preencha as quantidades dos produtos farmados\n"
                "4️⃣ Envie - Os registros serão salvos!\n\n"
                "💡 Deixe em branco os produtos que não foram farmados",
                ephemeral=True
            )
            return
        
        canal_nome = interaction.channel.name if hasattr(interaction.channel, 'name') else "desconhecido"
        modal = FarmModal(self.user_id, imagem_url, self.user_name, canal_nome)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Meu Histórico", style=discord.ButtonStyle.secondary, emoji="📊", row=0)
    async def historico(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Este canal é privado!", ephemeral=True)
            return
        
        user_data = dados["usuarios"].get(str(self.user_id), {"farms": [], "pagamentos": []})
        farms = user_data["farms"][-10:]
        
        if not farms:
            msg = "Você ainda não registrou nenhuma farm."
        else:
            msg = f"**SEUS ÚLTIMOS REGISTROS - {self.user_name}**\n\n"
            for i, f in enumerate(reversed(farms), 1):
                msg += f"Farm #{i}\n"
                msg += f"{f.get('produto', 'Desconhecido')}\n"
                msg += f"{f['quantidade']} itens\n"
                msg += f"{f['data']}\n"
                msg += f"[Print]({f['print_url']})\n\n"
        
        if len(msg) > 1900:
            with open(f"historico_{self.user_id}.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await interaction.response.send_message(file=discord.File(f"historico_{self.user_id}.txt"), ephemeral=True)
            os.remove(f"historico_{self.user_id}.txt")
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Meus Pagamentos", style=discord.ButtonStyle.primary, emoji="💰", row=0)
    async def meus_pagamentos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Este canal é privado!", ephemeral=True)
            return
        
        user_data = dados["usuarios"].get(str(self.user_id), {"farms": [], "pagamentos": []})
        pagamentos = user_data["pagamentos"]
        
        if not pagamentos:
            msg = "Você ainda não recebeu nenhum pagamento."
        else:
            total = sum(p["valor"] for p in pagamentos)
            msg = f"**TOTAL RECEBIDO: R$ {total:,.2f}**\n\n**HISTÓRICO DE PAGAMENTOS:**\n"
            for p in pagamentos[-10:]:
                tipo = p.get("tipo", "Pagamento")
                if tipo == "Fechamento de Caixa Semanal":
                    msg += f"**{tipo}**\n"
                    msg += f"   Salário: R$ {p.get('salario', 0):,.2f}\n"
                    msg += f"   Extra: R$ {p.get('extra', 0):,.2f}\n"
                    msg += f"   Total: R$ {p['valor']:,.2f}\n"
                    msg += f"   Admin: {p.get('admin_nome', 'Desconhecido')}\n"
                else:
                    msg += f"R$ {p['valor']:,.2f} - {p['data']}\n"
                msg += "\n"
        
        if len(msg) > 1900:
            with open(f"pagamentos_{self.user_id}.txt", "w", encoding="utf-8") as f:
                f.write(msg)
            await interaction.response.send_message(file=discord.File(f"pagamentos_{self.user_id}.txt"), ephemeral=True)
            os.remove(f"pagamentos_{self.user_id}.txt")
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem mudar o nome do canal!", ephemeral=True)
            return
        
        modal = MudarNomeModal(interaction.channel)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Fechar Caixa Semana", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem fechar caixa!", ephemeral=True)
            return
        
        modal = FechamentoCaixaModal(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal ou administradores podem ver!", ephemeral=True)
            return
        
        fechamentos = dados["caixa_semana"].get(str(self.user_id), [])
        
        if not fechamentos:
            await interaction.response.send_message("Nenhum fechamento de caixa registrado ainda!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="HISTÓRICO DE FECHAMENTO DE CAIXA",
            description=f"Últimos {min(10, len(fechamentos))} registros",
            color=discord.Color.blue()
        )
        
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M")
            lucro = fech['total'] - fech['salario'] - fech['extra']
            emoji_lucro = "📈" if lucro > 0 else "📉"
            
            embed.add_field(
                name=f"📅 {data}",
                value=f"Meta Farm: R$ {fech['meta_farm']:,.2f}\n"
                      f"Farm Sujo: R$ {fech['farm_sujo']:,.2f}\n"
                      f"Salário: R$ {fech['salario']:,.2f}\n"
                      f"Extra: R$ {fech['extra']:,.2f}\n"
                      f"**Total Bruto: R$ {fech['total']:,.2f}**\n"
                      f"**Valor Pago: R$ {fech.get('valor_pago', fech['salario'] + fech['extra']):,.2f}**\n"
                      f"{emoji_lucro} **Lucro Líquido: R$ {lucro:,.2f}**\n"
                      f"Admin: {fech['admin']}",
                inline=False
            )
        
        embed.set_footer(text="Clique em 'Fechar Caixa Semana' para adicionar novo registro")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem fechar canais!", ephemeral=True)
            return
        
        view = ConfirmarFechamentoView(self.user_id, interaction.channel)
        await interaction.response.send_message(
            "⚠️ Tem certeza que deseja fechar este canal?\n\nOs registros serão mantidos.",
            view=view,
            ephemeral=True
        )

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.canal = canal
    
    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        nome_canal = self.canal.name
        user = await bot.fetch_user(self.user_id) if self.user_id else None
        
        if str(self.user_id) in dados["canais"]:
            del dados["canais"][str(self.user_id)]
            salvar_dados()
        
        await self.canal.delete()
        await interaction.response.send_message("Canal fechado!", ephemeral=True)
        
        await log_acao(
            "fechar_canal",
            interaction.user,
            f"**Canal fechado:** {nome_canal}\n**Dono:** {user.mention if user else 'Desconhecido'}",
            0xff0000
        )
        
        await log_admin(
            "CANAL FECHADO",
            f"**Canal:** {nome_canal}\n**Dono:** {user.mention if user else 'Desconhecido'}\n**Fechado por:** {interaction.user.mention}",
            0xff0000
        )
        
        await atualizar_ranking()
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cancelado!", ephemeral=True)

# ========= MODAIS ADMIN =========
class AdicionarAdminModal(Modal, title="Adicionar Administrador"):
    identificador = TextInput(
        label="ID ou Nome do usuário",
        placeholder="Digite o ID (ex: 123456789) ou @nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Você não tem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        identificador = self.identificador.value.strip()
        usuario_alvo = None
        
        if identificador.isdigit():
            try:
                usuario_alvo = await interaction.client.fetch_user(int(identificador))
            except:
                pass
        
        if not usuario_alvo and interaction.guild:
            for member in interaction.guild.members:
                if member.name.lower() == identificador.lower() or member.display_name.lower() == identificador.lower():
                    usuario_alvo = member
                    break
        
        if not usuario_alvo:
            await interaction.followup.send(f"Usuário não encontrado!", ephemeral=True)
            return
        
        if str(usuario_alvo.id) in dados["admins"]:
            await interaction.followup.send(f"{usuario_alvo.mention} já é administrador!", ephemeral=True)
            return
        
        dados["admins"].append(str(usuario_alvo.id))
        salvar_dados()
        
        await interaction.followup.send(f"{usuario_alvo.mention} agora é administrador!", ephemeral=True)
        
        await log_acao("setar_admin", interaction.user, f"Novo admin: {usuario_alvo.mention}", 0x9b59b6)
        await log_admin("NOVO ADMIN", f"**Adicionado por:** {interaction.user.mention}\n**Novo admin:** {usuario_alvo.mention}", 0x9b59b6)

class RemoverAdminModal(Modal, title="Remover Administrador"):
    identificador = TextInput(
        label="ID ou Nome do usuário",
        placeholder="Digite o ID (ex: 123456789) ou @nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Você não tem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        identificador = self.identificador.value.strip()
        usuario_alvo = None
        
        if identificador.isdigit():
            try:
                usuario_alvo = await interaction.client.fetch_user(int(identificador))
            except:
                pass
        
        if not usuario_alvo and interaction.guild:
            for member in interaction.guild.members:
                if member.name.lower() == identificador.lower() or member.display_name.lower() == identificador.lower():
                    usuario_alvo = member
                    break
        
        if not usuario_alvo:
            await interaction.followup.send(f"Usuário não encontrado!", ephemeral=True)
            return
        
        if str(usuario_alvo.id) not in dados["admins"]:
            await interaction.followup.send(f"{usuario_alvo.mention} não é administrador!", ephemeral=True)
            return
        
        dados["admins"].remove(str(usuario_alvo.id))
        salvar_dados()
        
        await interaction.followup.send(f"{usuario_alvo.mention} não é mais administrador!", ephemeral=True)
        
        await log_acao("setar_admin", interaction.user, f"Admin removido: {usuario_alvo.mention}", 0xff0000)
        await log_admin("ADMIN REMOVIDO", f"**Removido por:** {interaction.user.mention}\n**Ex-admin:** {usuario_alvo.mention}", 0xff0000)

class PagamentoModal(Modal, title="Pagamento Manual"):
    user_id_text = TextInput(label="ID do usuário", placeholder="Digite o ID", required=True)
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 500", required=True)
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        try:
            user_id = int(self.user_id_text.value)
            valor_pag = int(self.valor.value)
        except ValueError:
            await interaction.response.send_message("ID ou valor inválido!", ephemeral=True)
            return
        
        if str(user_id) not in dados["usuarios"]:
            dados["usuarios"][str(user_id)] = {"farms": [], "pagamentos": []}
        
        dados["usuarios"][str(user_id)]["pagamentos"].append({
            "valor": valor_pag,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id,
            "admin_nome": interaction.user.name,
            "tipo": "Pagamento Manual"
        })
        salvar_dados()
        
        try:
            membro = await interaction.client.fetch_user(user_id)
            await membro.send(f"Você recebeu um pagamento manual de R$ {valor_pag:,.2f}!\nAdmin: {interaction.user.name}")
        except:
            pass
        
        await interaction.response.send_message(f"Pago R$ {valor_pag:,.2f} para <@{user_id}>!", ephemeral=True)
        
        await log_acao("pagar", interaction.user, f"Valor: R${valor_pag}\nDestinatário: <@{user_id}>", 0xffa500)
        await log_admin("PAGAMENTO MANUAL", f"**Admin:** {interaction.user.mention}\n**Valor:** R$ {valor_pag:,.2f}\n**Destinatário:** <@{user_id}>", 0xffa500)
        
        await atualizar_ranking()

# ========= PAINEL DO ADMIN =========
class AdminPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Pagar Membro", style=discord.ButtonStyle.success, emoji="💰")
    async def pagar_membro(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        modal = PagamentoModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Top da Semana", style=discord.ButtonStyle.primary, emoji="🏆")
    async def top_semana(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        semana_atras = datetime.now() - timedelta(days=7)
        ranking = []
        
        for user_id, data in dados["usuarios"].items():
            total = 0
            for farm in data["farms"]:
                try:
                    data_farm = datetime.strptime(farm["data"], "%Y-%m-%d %H:%M:%S")
                    if data_farm >= semana_atras:
                        total += farm["quantidade"]
                except:
                    pass
            if total > 0:
                ranking.append((int(user_id), total))
        
        if not ranking:
            await interaction.response.send_message("Ninguém farmou esta semana!", ephemeral=True)
            return
        
        ranking.sort(key=lambda x: x[1], reverse=True)
        embed = discord.Embed(title="TOP FARMERS DA SEMANA", color=discord.Color.gold())
        
        for i, (user_id, total) in enumerate(ranking[:10], 1):
            try:
                user = await interaction.client.fetch_user(user_id)
                medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
                embed.add_field(name=f"{medalha} {user.name}", value=f"{total} itens", inline=False)
            except:
                continue
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    @discord.ui.button(label="Relatório", style=discord.ButtonStyle.secondary, emoji="📋")
    async def relatorio(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        relatorio = f"RELATÓRIO GERAL\n📅 {datetime.now().strftime('%d/%m/%Y')}\nUsuários: {len(dados['usuarios'])}\nAdmins: {len(dados['admins'])}\n\n"
        
        for user_id, data in dados["usuarios"].items():
            try:
                user = await interaction.client.fetch_user(int(user_id))
                total_farms = len(data["farms"])
                total_qtd = sum(f["quantidade"] for f in data["farms"])
                total_pag = sum(p["valor"] for p in data["pagamentos"])
                relatorio += f"{user.name}:\n   Farms: {total_farms}\n   Total: {total_qtd}\n   Recebido: R$ {total_pag:,.2f}\n\n"
            except:
                continue
        
        with open("relatorio.txt", "w", encoding="utf-8") as f:
            f.write(relatorio)
        
        await interaction.followup.send("Relatório!", file=discord.File("relatorio.txt"), ephemeral=True)
        os.remove("relatorio.txt")
    
    @discord.ui.button(label="Adicionar Admin", style=discord.ButtonStyle.danger, emoji="👑")
    async def add_admin(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        modal = AdicionarAdminModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remover Admin", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_admin(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        modal = RemoverAdminModal()
        await interaction.response.send_modal(modal)

# ========= BOTÃO PRINCIPAL =========
class BotaoCriarCanalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        
        if interaction.guild is None:
            await interaction.response.send_message("Use em um servidor!", ephemeral=True)
            return
        
        if not interaction.guild.me.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "Bot precisa de permissão de Administrador.",
                ephemeral=True
            )
            return
        
        if str(interaction.user.id) in dados["canais"]:
            canal_id = dados["canais"][str(interaction.user.id)]
            canal = interaction.guild.get_channel(canal_id)
            if canal:
                await interaction.response.send_message(
                    f"Você já possui um canal privado! Acesse: {canal.mention}",
                    ephemeral=True
                )
                return
            else:
                del dados["canais"][str(interaction.user.id)]
                salvar_dados()
        
        await interaction.response.send_message(
            "🔄 Criando seu canal privado...\nAguarde alguns segundos.",
            ephemeral=True
        )
        
        try:
            categoria_farms = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria_farms or not isinstance(categoria_farms, discord.CategoryChannel):
                await interaction.edit_original_response(
                    content=f"Erro: Categoria de farms não encontrada!"
                )
                return
            
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, attach_files=True, 
                    embed_links=True, add_reactions=True, read_message_history=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_channels=True,
                    attach_files=True, embed_links=True, read_message_history=True
                )
            }
            
            cargo_admin = interaction.guild.get_role(CARGO_ADMIN_ID)
            if cargo_admin:
                overwrites[cargo_admin] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, attach_files=True,
                    embed_links=True, manage_channels=True
                )
            
            for admin_id in dados["admins"]:
                admin_member = interaction.guild.get_member(int(admin_id))
                if admin_member:
                    overwrites[admin_member] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, attach_files=True,
                        embed_links=True, manage_channels=True
                    )
            
            for member in interaction.guild.members:
                if member.guild_permissions.administrator:
                    overwrites[member] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, attach_files=True,
                        embed_links=True, manage_channels=True
                    )
            
            nome_canal = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
            canal = await categoria_farms.create_text_channel(nome_canal, overwrites=overwrites)
            
            dados["canais"][str(interaction.user.id)] = canal.id
            salvar_dados()
            
            embed = discord.Embed(
                title="SEU CANAL PRIVADO DE FARMS",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n"
                           "Este é o seu **canal exclusivo** para registrar suas farms.\n"
                           "🔒 Apenas **você** e os **administradores** têm acesso.\n\n"
                           "**COMO REGISTRAR UMA FARM:**\n"
                           "1️⃣ Anexe a print da farm (botão 📎)\n"
                           "2️⃣ Clique em Nova Farm\n"
                           "3️⃣ Preencha as quantidades\n"
                           "4️⃣ Envie\n\n"
                           "**OUTROS BOTÕES:**\n"
                           "• Meu Histórico - Ver farms\n"
                           "• Meus Pagamentos - Ver ganhos\n"
                           "• Mudar Nome - APENAS ADMIN\n"
                           "• Fechar Caixa Semana - ADM\n"
                           "• Histórico Caixa - Ver fechamentos\n"
                           "• Fechar Canal - ADM\n\n"
                           "👑 Apenas administradores podem usar botões administrativos",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Canal criado em {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            
            view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
            await canal.send(embed=embed, view=view)
            await canal.send("📌 Para registrar: 1️⃣ Anexe a print | 2️⃣ Clique em Nova Farm | 3️⃣ Preencha as quantidades | 4️⃣ Envie")
            
            await log_acao(
                "criar_canal",
                interaction.user,
                f"Canal criado: {canal.mention}",
                0x00ff00
            )
            
            await log_criar_canal(interaction.user, canal)
            
            await interaction.edit_original_response(
                content=f"Canal privado criado!\n\nAcesse: {canal.mention}"
            )
            
            await atualizar_ranking()
            
        except Exception as e:
            await log_acao("erro", None, f"Erro ao criar canal: {str(e)}", 0xff0000)
            await interaction.edit_original_response(
                content=f"Erro: {str(e)[:200]}"
            )

# ========= COMANDOS =========
@bot.command(name="admin")
async def admin_panel(ctx):
    """Painel administrativo"""
    if not is_admin(ctx.author):
        await ctx.send("Acesso negado! Apenas administradores.")
        return
    
    num_admins = len(dados["admins"])
    
    view = AdminPanelView()
    embed = discord.Embed(
        title="PAINEL ADMINISTRATIVO",
        description=f"Cargo Admin ID: `{CARGO_ADMIN_ID}`\n"
                   f"Admins cadastrados: {num_admins}\n\n"
                   "Botões disponíveis:\n"
                   "💰 Pagar Membro - Pagamento manual\n"
                   "🏆 Top da Semana - Ranking semanal\n"
                   "📋 Relatório - Relatório geral\n"
                   "👑 Adicionar Admin\n"
                   "🗑️ Remover Admin",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, view=view)

@bot.command(name="atualizar_rank")
async def atualizar_rank_comando(ctx):
    """Atualiza o ranking manualmente"""
    if not is_admin(ctx.author):
        await ctx.send("Apenas administradores!")
        return
    
    await atualizar_ranking()
    await ctx.send("Ranking atualizado!")

@bot.command(name="resetar_rank")
async def resetar_rank_comando(ctx):
    """Reseta o ranking (apenas admin)"""
    if not is_admin(ctx.author):
        await ctx.send("Apenas administradores!")
        return
    
    view = ConfirmarResetView()
    await ctx.send(
        "⚠️ **ATENÇÃO!** ⚠️\n\n"
        "Você tem certeza que deseja RESETAR TODO O RANKING?\n\n"
        "Isso irá:\n"
        "• Apagar todas as farms registradas\n"
        "• Apagar todos os pagamentos\n"
        "• Apagar todo o histórico de caixa\n\n"
        "**Um backup será salvo automaticamente antes do reset.**\n\n"
        "Esta ação é IRREVERSÍVEL!",
        view=view
    )

# ========= EVENTOS =========
@bot.event
async def on_ready():
    print(f"Bot {bot.user} está online!")
    print(f"Conectado a {len(bot.guilds)} servidores")
    
    # Verificar canais de log
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        print(f"Canal de logs encontrado: #{canal_logs.name}")
    else:
        print(f"Canal de logs ID {CHAT_LOGS_ID} NÃO ENCONTRADO!")
    
    canal_admin_logs = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal_admin_logs:
        print(f"Canal de admin logs encontrado: #{canal_admin_logs.name}")
    else:
        print(f"Canal de admin logs ID {CHAT_ADMIN_LOGS_ID} NÃO ENCONTRADO!")
    
    for guild in bot.guilds:
        print(f"\nServidor: {guild.name}")
        
        # Verificar cargo admin
        cargo_admin = guild.get_role(CARGO_ADMIN_ID)
        if cargo_admin:
            print(f"  Cargo Admin encontrado: {cargo_admin.name}")
        else:
            print(f"  Cargo Admin ID {CARGO_ADMIN_ID} não encontrado!")
        
        # Configurar canal de compra e venda
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas:
            print(f"  Canal de compra/venda encontrado: #{canal_vendas.name}")
            
            async for msg in canal_vendas.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()
            
            embed_vendas = discord.Embed(
                title="SISTEMA DE COMPRA E VENDA",
                description="Clique nos botões abaixo para registrar compras ou vendas!\n\n"
                           "💸 Venda de Munição: Registre vendas de munição\n"
                           "🛒 Compra de Produto: Registre compras de produtos",
                color=discord.Color.blue()
            )
            view_vendas = CompraVendaView()
            await canal_vendas.send(embed=embed_vendas, view=view_vendas)
            print(f"  Botões de compra/venda configurados!")
        else:
            print(f"  Canal de compra/venda ID {CHAT_COMPRA_VENDA_ID} NÃO ENCONTRADO!")
        
        # Configurar canal de criar canal
        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel and isinstance(categoria_painel, discord.CategoryChannel):
            print(f"  Categoria do PAINEL encontrada: {categoria_painel.name}")
            
            canal_criar = None
            for channel in categoria_painel.channels:
                if channel.name == "criar-canal" and isinstance(channel, discord.TextChannel):
                    canal_criar = channel
                    break
            
            if not canal_criar:
                try:
                    canal_criar = await categoria_painel.create_text_channel("criar-canal")
                    print(f"  Canal 'criar-canal' criado!")
                except Exception as e:
                    print(f"  Erro ao criar canal: {e}")
                    continue
            
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            
            embed = discord.Embed(
                title="SISTEMA DE FARM",
                description="Clique no botão abaixo para criar seu canal privado!\n\n"
                           "🔒 Apenas você e os administradores terão acesso",
                color=discord.Color.blue()
            )
            view = BotaoCriarCanalView()
            await canal_criar.send(embed=embed, view=view)
            print(f"  Painel de criação configurado!")
        else:
            print(f"  Categoria do PAINEL ID {CATEGORIA_PAINEL_ID} NÃO ENCONTRADA!")
        
        # Verificar categoria de farms
        categoria_farms = guild.get_channel(CATEGORIA_FARMS_ID)
        if categoria_farms and isinstance(categoria_farms, discord.CategoryChannel):
            print(f"  Categoria FARMS PRIVADAS encontrada: {categoria_farms.name}")
        else:
            print(f"  Categoria FARMS PRIVADAS ID {CATEGORIA_FARMS_ID} NÃO ENCONTRADA!")
    
    await atualizar_ranking()
    
    # Enviar mensagem de boas vindas nos canais de log
    await log_admin("BOT INICIADO", f"Bot {bot.user.mention} está online!\nComandos: !admin, !atualizar_rank, !resetar_rank", 0x00ff00)
    
    print(f"\nBOT PRONTO!")
    print(f"Comandos: !admin, !atualizar_rank, !resetar_rank")

# ========= INICIAR =========
if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
