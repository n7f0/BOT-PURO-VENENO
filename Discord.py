import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import aiohttp
import shutil
from pathlib import Path

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
CATEGORIA_BACKUP_ID = int(os.getenv("CATEGORIA_BACKUP_ID", "1498305209175380080"))
CATEGORIA_COMPRA_VENDA_LOGS_ID = int(os.getenv("CATEGORIA_COMPRA_VENDA_LOGS_ID", "1498305956235448390"))
CATEGORIA_ADMIN_PAINEL_ID = int(os.getenv("CATEGORIA_ADMIN_PAINEL_ID", "1498318907792953374"))
CHAT_ADMIN_PAINEL_ID = int(os.getenv("CHAT_ADMIN_PAINEL_ID", "1498334105908150332"))  # Chat específico do painel admin
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
    "compras_vendas": [],
    "usuarios_banidos": [],
    "dinheiro_sujo": {}
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

async def criar_canal_backup(tipo, nome_arquivo=None):
    categoria = bot.get_channel(CATEGORIA_BACKUP_ID)
    if not categoria or not isinstance(categoria, discord.CategoryChannel):
        return None
    
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    
    if tipo == "novo":
        nome_canal = f"backup-novo-{data}"
        canal = await categoria.create_text_channel(nome_canal)
        
        embed = discord.Embed(
            title="NOVO BACKUP CRIADO",
            description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            color=discord.Color.green()
        )
        await canal.send(embed=embed)
        
        if nome_arquivo and os.path.exists(nome_arquivo):
            await canal.send(file=discord.File(nome_arquivo))
        
        return canal
    
    elif tipo == "deletado":
        nome_canal = f"backup-deletado-{data}"
        canal = await categoria.create_text_channel(nome_canal)
        
        embed = discord.Embed(
            title="BACKUP DELETADO",
            description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            color=discord.Color.red()
        )
        await canal.send(embed=embed)
        
        return canal

async def criar_canal_compra_venda_log(tipo, dados_log):
    categoria = bot.get_channel(CATEGORIA_COMPRA_VENDA_LOGS_ID)
    if not categoria or not isinstance(categoria, discord.CategoryChannel):
        return None
    
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    nome_canal = f"log-{tipo}-{data}"
    canal = await categoria.create_text_channel(nome_canal)
    
    embed = discord.Embed(
        title=f"LOG DE {tipo.upper()}",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    for chave, valor in dados_log.items():
        embed.add_field(name=chave, value=valor, inline=False)
    
    await canal.send(embed=embed)
    return canal

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]:
        return 0
    
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    
    canais_para_verificar = [
        CHAT_LOGS_ID,
        CHAT_ADMIN_LOGS_ID,
        CHAT_RANK_ID,
        CHAT_COMPRA_VENDA_ID
    ]
    
    for canal_id in canais_para_verificar:
        canal = bot.get_channel(canal_id)
        if canal and isinstance(canal, discord.TextChannel):
            try:
                async for mensagem in canal.history(limit=None):
                    if mensagem.author == bot.user:
                        if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                            novo_conteudo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                            novo_conteudo = novo_conteudo.replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                            try:
                                await mensagem.edit(content=novo_conteudo)
                                total_limpo += 1
                            except:
                                pass
            except:
                pass
    
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal and isinstance(canal, discord.TextChannel):
            try:
                async for mensagem in canal.history(limit=None):
                    if mensagem.author == bot.user:
                        if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                            novo_conteudo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                            novo_conteudo = novo_conteudo.replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                            try:
                                await mensagem.edit(content=novo_conteudo)
                                total_limpo += 1
                            except:
                                pass
            except:
                pass
    
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {
            "farms": [],
            "pagamentos": [],
            "dinheiro_sujo": 0,
            "nome": f"[REMOVIDO - {user_name}]",
            "removido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "removido_por": "sistema"
        }
        salvar_dados()
    
    if str(user_id) in dados["canais"]:
        canal_id = dados["canais"][str(user_id)]
        canal = bot.get_channel(canal_id)
        if canal:
            try:
                await canal.delete(reason=f"Usuário {user_name} removido do sistema")
            except:
                pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    
    return total_limpo

# ========= FUNÇÕES PARA ENVIAR LOGS =========
async def log_acao(acao, usuario, detalhes, cor=None):
    cores = {
        "criar_canal": 0x00ff00,
        "registrar_farm": 0x00ff00,
        "registrar_dinheiro_sujo": 0xff0000,
        "pagar": 0xffa500,
        "fechar_canal": 0xff0000,
        "fechar_caixa": 0xffa500,
        "reset_rank": 0xff0000,
        "erro": 0xff0000,
        "info": 0x3498db,
        "admin": 0x9b59b6,
        "setar_admin": 0x9b59b6,
        "compra_venda": 0x00ff00,
        "usuario_removido": 0xff0000
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

# ========= FUNÇÃO PARA ATUALIZAR RANKING =========
async def atualizar_ranking():
    canal_rank = bot.get_channel(CHAT_RANK_ID)
    if not canal_rank or not isinstance(canal_rank, discord.TextChannel):
        return
    
    async for msg in canal_rank.history(limit=50):
        if msg.author == bot.user:
            await msg.delete()
    
    usuarios_data = []
    for user_id, data in dados["usuarios"].items():
        if "removido_em" in data:
            continue
            
        try:
            user = await bot.fetch_user(int(user_id))
            
            total_chumbo = 0
            total_capsula = 0
            total_polvora = 0
            
            for farm in data["farms"]:
                for produto in farm.get("produtos", []):
                    qtd = produto["quantidade"]
                    if produto["produto"] == "CHUMBO":
                        total_chumbo += qtd
                    elif produto["produto"] == "CAPSULA":
                        total_capsula += qtd
                    elif produto["produto"] == "POLVORA":
                        total_polvora += qtd
            
            total_pagamentos = sum(p["valor"] for p in data["pagamentos"])
            quantidade_pagamentos = len(data["pagamentos"])
            dinheiro_sujo = data.get("dinheiro_sujo", 0)
            
            usuarios_data.append({
                "nome": user.name,
                "user_id": user_id,
                "total_chumbo": total_chumbo,
                "total_capsula": total_capsula,
                "total_polvora": total_polvora,
                "total_pagamentos": total_pagamentos,
                "quantidade_pagamentos": quantidade_pagamentos,
                "dinheiro_sujo": dinheiro_sujo
            })
        except:
            continue
    
    ranking_chumbo = sorted(usuarios_data, key=lambda x: x["total_chumbo"], reverse=True)[:5]
    ranking_capsula = sorted(usuarios_data, key=lambda x: x["total_capsula"], reverse=True)[:5]
    ranking_polvora = sorted(usuarios_data, key=lambda x: x["total_polvora"], reverse=True)[:5]
    ranking_salario = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:5]
    ranking_dinheiro_sujo = sorted(usuarios_data, key=lambda x: x["dinheiro_sujo"], reverse=True)[:5]
    
    embed = discord.Embed(
        title="RANKING GERAL",
        description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        color=discord.Color.gold()
    )
    
    ranking_text = ""
    for i, u in enumerate(ranking_chumbo, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        if u['total_chumbo'] > 0:
            ranking_text += f"{medalha} **{u['nome']}** - {u['total_chumbo']:,} itens\n"
    embed.add_field(name="CHUMBO", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_capsula, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        if u['total_capsula'] > 0:
            ranking_text += f"{medalha} **{u['nome']}** - {u['total_capsula']:,} itens\n"
    embed.add_field(name="CAPSULA", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_polvora, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        if u['total_polvora'] > 0:
            ranking_text += f"{medalha} **{u['nome']}** - {u['total_polvora']:,} itens\n"
    embed.add_field(name="POLVORA", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_salario, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        if u['total_pagamentos'] > 0:
            ranking_text += f"{medalha} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pagamentos)\n"
    embed.add_field(name="TOP SALÁRIO", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
    ranking_text = ""
    for i, u in enumerate(ranking_dinheiro_sujo, 1):
        medalha = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}°"
        if u['dinheiro_sujo'] > 0:
            ranking_text += f"{medalha} **{u['nome']}** - R$ {u['dinheiro_sujo']:,.2f}\n"
    embed.add_field(name="DINHEIRO SUJO", value=ranking_text if ranking_text else "Nenhum dado ainda", inline=False)
    
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
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        view = ConfirmarResetView()
        await interaction.response.send_message(
            "⚠️ ATENÇÃO! ⚠️\n\n"
            "Você tem certeza que deseja RESETAR TODO O RANKING?\n\n"
            "Isso irá:\n"
            "• Apagar todas as farms registradas\n"
            "• Apagar todos os pagamentos\n"
            "• Apagar todo o histórico de caixa\n\n"
            "Um backup será salvo automaticamente antes do reset.\n\n"
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
        
        backup_nome = f"backup_rank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup = {
            "usuarios": dados["usuarios"].copy(),
            "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name
        }
        
        with open(backup_nome, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)
        
        await criar_canal_backup("novo", backup_nome)
        
        dados["usuarios"] = {}
        dados["caixa_semana"] = {}
        dados["dinheiro_sujo"] = {}
        salvar_dados()
        
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0xff0000)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0xff0000)
        
        await interaction.followup.send("Ranking resetado com sucesso! Um backup foi salvo.", ephemeral=True)
        await atualizar_ranking()
        self.stop()
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

# ========= MODAL PARA REGISTRAR DINHEIRO SUJO =========
class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    quantidade = TextInput(
        label="Valor (R$)",
        placeholder="Ex: 5000",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, user_id, user_name, canal, imagem_url):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.imagem_url = imagem_url
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            valor = float(self.quantidade.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0}
        
        if "dinheiro_sujo" not in dados["usuarios"][str(self.user_id)]:
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0
        
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] += valor
        salvar_dados()
        
        embed = discord.Embed(
            title="💰 DINHEIRO SUJO REGISTRADO",
            description=f"**Usuário:** {self.user_name}\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_image(url=self.imagem_url)
        await self.canal.send(embed=embed)
        
        await interaction.followup.send(f"R$ {valor:,.2f} registrado como dinheiro sujo para {self.user_name}!", ephemeral=True)
        
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xff0000)
        
        await atualizar_ranking()

# ========= MODAL PARA REGISTRAR PRODUTOS (FARM PRODUTOS) =========
class FarmProdutosModal(Modal, title="Registrar Farm Produtos"):
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
            await interaction.followup.send("Nenhum produto válido! Preencha pelo menos um produto.", ephemeral=True)
            return
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0}
        
        farm_registro = {
            "produtos": produtos_registrados,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "print_url": self.imagem_url,
            "validado": True,
            "farm_id": len(dados["usuarios"][str(self.user_id)]["farms"]) + 1
        }
        
        dados["usuarios"][str(self.user_id)]["farms"].append(farm_registro)
        salvar_dados()
        
        embed = discord.Embed(
            title="FARM PRODUTOS REGISTRADA COM SUCESSO",
            color=discord.Color.green()
        )
        
        descricao = ""
        for produto in produtos_registrados:
            if produto["produto"] == "CHUMBO":
                descricao += f"🔫 **{produto['produto']}:** {produto['quantidade']} itens\n"
            elif produto["produto"] == "CAPSULA":
                descricao += f"💣 **{produto['produto']}:** {produto['quantidade']} itens\n"
            elif produto["produto"] == "POLVORA":
                descricao += f"💥 **{produto['produto']}:** {produto['quantidade']} itens\n"
        
        embed.description = descricao
        embed.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
        embed.set_image(url=self.imagem_url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        produtos_str = ", ".join([f"{p['produto']}: {p['quantidade']}" for p in produtos_registrados])
        await log_acao("registrar_farm", interaction.user, f"Produtos: {produtos_str}")
        await log_admin("NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {produtos_str}", 0x00ff00)
        
        await atualizar_ranking()

# ========= MODAL DE PAGAMENTO COM PRINT =========
class PagamentoFarmModal(Modal, title="Registrar Pagamento"):
    valor = TextInput(
        label="Valor do Pagamento (R$)",
        placeholder="Ex: 500",
        required=True,
        style=discord.TextStyle.short
    )
    
    def __init__(self, user_id, user_name, canal, imagem_url):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal
        self.imagem_url = imagem_url
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            valor = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.followup.send("Valor inválido!", ephemeral=True)
            return
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0}
        
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id,
            "admin_nome": interaction.user.name,
            "tipo": "Pagamento",
            "print_url": self.imagem_url
        })
        salvar_dados()
        
        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            embed_notificacao = discord.Embed(
                title="PAGAMENTO RECEBIDO",
                description=f"Você recebeu um pagamento de **R$ {valor:,.2f}**!",
                color=discord.Color.green()
            )
            embed_notificacao.add_field(name="Admin Responsável", value=interaction.user.mention, inline=True)
            embed_notificacao.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
            embed_notificacao.set_image(url=self.imagem_url)
            await user.send(embed=embed_notificacao)
        except:
            pass
        
        embed = discord.Embed(
            title="PAGAMENTO REGISTRADO",
            description=f"**Usuário:** {self.user_name}\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_image(url=self.imagem_url)
        await self.canal.send(embed=embed)
        
        await interaction.followup.send(f"Pagamento de R$ {valor:,.2f} registrado para {self.user_name}!", ephemeral=True)
        
        await log_acao("pagar", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xffa500)
        await log_admin("PAGAMENTO", f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}\nAdmin: {interaction.user.mention}", 0xffa500)
        
        await atualizar_ranking()

# ========= MODAL PARA FECHAMENTO DE CAIXA =========
class FechamentoCaixaModal(Modal, title="Fechamento de Caixa da Semana"):
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
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            sujo = float(self.farm_sujo.value.replace(",", "."))
            salario_valor = float(self.salario.value.replace(",", "."))
            extra_valor = float(self.extra.value.replace(",", "."))
            total = sujo + salario_valor + extra_valor
        except ValueError:
            await interaction.followup.send("Valores inválidos!", ephemeral=True)
            return
        
        valor_pagamento = salario_valor + extra_valor
        
        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms": [], "pagamentos": [], "nome": self.user_name, "dinheiro_sujo": 0}
        
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor_pagamento,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id,
            "admin_nome": interaction.user.name,
            "tipo": "Fechamento de Caixa Semanal",
            "salario": salario_valor,
            "extra": extra_valor,
            "farm_sujo": sujo
        })
        
        fechamento = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name,
            "admin_id": interaction.user.id,
            "usuario": self.user_name,
            "usuario_id": self.user_id,
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
                title="FECHAMENTO DE CAIXA",
                description=f"Registrado para {self.user_name}!",
                color=discord.Color.orange()
            )
            embed_notificacao.add_field(name="Farm Sujo", value=f"R$ {sujo:,.2f}", inline=True)
            embed_notificacao.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
            embed_notificacao.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
            embed_notificacao.add_field(name="Total Recebido", value=f"R$ {valor_pagamento:,.2f}", inline=True)
            embed_notificacao.add_field(name="Admin", value=interaction.user.mention, inline=True)
            await user.send(embed=embed_notificacao)
        except:
            pass
        
        embed = discord.Embed(
            title="FECHAMENTO DE CAIXA SEMANAL",
            description=f"**{self.user_name}**, fechamento registrado!",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="Farm Sujo", value=f"R$ {sujo:,.2f}", inline=True)
        embed.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
        embed.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
        embed.add_field(name="TOTAL BRUTO", value=f"R$ {total:,.2f}", inline=True)
        embed.add_field(name="PAGAMENTO REALIZADO", value=f"R$ {valor_pagamento:,.2f}", inline=True)
        embed.add_field(name="Lucro Líquido", value=f"R$ {lucro_liquido:,.2f}", inline=True)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        
        await self.canal.send(embed=embed)
        await interaction.followup.send(f"Fechamento de caixa registrado! Pagamento de R$ {valor_pagamento:,.2f} realizado.", ephemeral=True)
        
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nPagamento: R$ {valor_pagamento}", 0xffa500)
        await log_admin("FECHAMENTO DE CAIXA", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}\nTotal Pago: R$ {valor_pagamento:,.2f}", 0xffa500)
        
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
        placeholder="Ex: Primeiro Comando",
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
        
        dados_log = {
            "Tipo": "VENDA",
            "Quantidade": f"{qtd:,} munições",
            "Valor Total": f"R$ {valor:,.2f}",
            "Facção Compradora": faccao,
            "Responsável": responsavel_nome,
            "Registrado por": interaction.user.mention
        }
        await criar_canal_compra_venda_log("venda", dados_log)
        
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
            await interaction.followup.send("Canal de vendas não encontrado!", ephemeral=True)
        
        await log_acao("compra_venda", interaction.user, f"Venda: {qtd} munições - R$ {valor}", 0x00ff00)

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
        placeholder="Ex: Primeiro Comando",
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
        
        dados_log = {
            "Tipo": "COMPRA",
            "Quantidade": f"{qtd:,}",
            "Produto": produto_nome,
            "Valor Total": f"R$ {valor:,.2f}",
            "Facção Vendedora": faccao,
            "Responsável": responsavel_nome,
            "Registrado por": interaction.user.mention
        }
        await criar_canal_compra_venda_log("compra", dados_log)
        
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
            await interaction.followup.send("Canal de vendas não encontrado!", ephemeral=True)
        
        await log_acao("compra_venda", interaction.user, f"Compra: {qtd} x {produto_nome} - R$ {valor}", 0x00ff00)

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
        placeholder="Ex: farm-lucas",
        required=True,
        style=discord.TextStyle.short,
        max_length=90
    )
    
    def __init__(self, canal_atual):
        super().__init__()
        self.canal_atual = canal_atual
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        novo_nome = self.novo_nome.value.lower().replace(" ", "-")
        novo_nome = ''.join(c for c in novo_nome if c.isalnum() or c == '-')
        if not novo_nome:
            novo_nome = "farm"
        
        try:
            await self.canal_atual.edit(name=novo_nome)
            await interaction.response.send_message(f"Nome alterado para: {novo_nome}", ephemeral=True)
            await log_acao("info", interaction.user, f"Canal renomeado para: {novo_nome}", 0x3498db)
        except Exception as e:
            await interaction.response.send_message(f"Erro: {str(e)[:100]}", ephemeral=True)

# ========= VIEW DO CANAL PRIVADO - APENAS DONO (MEMBROS) =========
class FarmChannelViewMembro(View):
    """View que MEMBROS (dono do canal) vêem - APENAS botões Farm Produtos e Farm Dinheiro Sujo"""
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id
    
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal pode usar este botão!", ephemeral=True)
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
            await interaction.response.send_message("❌ Anexe a print da farm primeiro!", ephemeral=True)
            return
        
        modal = FarmProdutosModal(self.user_id, imagem_url, self.user_name, interaction.channel.name)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem registrar dinheiro sujo!", ephemeral=True)
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
            await interaction.response.send_message("❌ Anexe a print do comprovante de dinheiro sujo primeiro!", ephemeral=True)
            return
        
        modal = DinheiroSujoModal(self.user_id, self.user_name, interaction.channel, imagem_url)
        await interaction.response.send_modal(modal)

# ========= VIEW DO CANAL PRIVADO - ADMIN (COM TODOS OS BOTÕES) =========
class FarmChannelViewAdmin(View):
    """View que ADMINISTRADORES vêem (com todos os botões)"""
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.user_name = user_name
        self.canal_id = canal_id
    
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user):
            await interaction.response.send_message("Apenas o dono do canal pode usar este botão!", ephemeral=True)
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
            await interaction.response.send_message("❌ Anexe a print da farm primeiro!", ephemeral=True)
            return
        
        modal = FarmProdutosModal(self.user_id, imagem_url, self.user_name, interaction.channel.name)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem registrar dinheiro sujo!", ephemeral=True)
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
            await interaction.response.send_message("❌ Anexe a print do comprovante de dinheiro sujo primeiro!", ephemeral=True)
            return
        
        modal = DinheiroSujoModal(self.user_id, self.user_name, interaction.channel, imagem_url)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Meu Histórico", style=discord.ButtonStyle.secondary, emoji="📊", row=1)
    async def historico(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        user_data = dados["usuarios"].get(str(self.user_id), {"farms": [], "pagamentos": [], "nome": self.user_name})
        farms = user_data["farms"][-10:]
        
        if not farms:
            msg = "Nenhuma farm registrada."
        else:
            msg = f"HISTÓRICO - {self.user_name}\n\n"
            for i, f in enumerate(reversed(farms), 1):
                msg += f"Farm #{i}\n"
                for produto in f.get('produtos', []):
                    msg += f"• {produto['produto']}: {produto['quantidade']} itens\n"
                msg += f"📅 {f['data']}\n📸 [Print]({f['print_url']})\n\n"
        
        if len(msg) > 1900:
            with open(f"historico_{self.user_id}.txt", "w") as f:
                f.write(msg)
            await interaction.response.send_message(file=discord.File(f"historico_{self.user_id}.txt"), ephemeral=True)
            os.remove(f"historico_{self.user_id}.txt")
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Meus Pagamentos", style=discord.ButtonStyle.primary, emoji="💰", row=1)
    async def meus_pagamentos(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        user_data = dados["usuarios"].get(str(self.user_id), {"farms": [], "pagamentos": [], "nome": self.user_name})
        pagamentos = user_data["pagamentos"]
        
        if not pagamentos:
            msg = "Nenhum pagamento recebido."
        else:
            total = sum(p["valor"] for p in pagamentos)
            msg = f"TOTAL RECEBIDO: R$ {total:,.2f}\n\n"
            for p in pagamentos[-10:]:
                if p.get("tipo") == "Fechamento de Caixa Semanal":
                    msg += f"Fechamento: R$ {p['valor']:,.2f}\n   Salário: R$ {p.get('salario', 0):,.2f} | Extra: R$ {p.get('extra', 0):,.2f}\n"
                else:
                    msg += f"Pagamento: R$ {p['valor']:,.2f}\n"
                msg += f"   Admin: {p.get('admin_nome', 'Desconhecido')}\n   📅 {p['data']}\n"
                if p.get('print_url'):
                    msg += f"   📸 [Print]({p['print_url']})\n"
                msg += "\n"
        
        await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Registrar Pagamento", style=discord.ButtonStyle.success, emoji="💰", row=1)
    async def registrar_pagamento(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        imagem_url = None
        async for msg in interaction.channel.history(limit=10):
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        imagem_url = attachment.url
                        break
                if imagem_url:
                    break
        
        if not imagem_url:
            await interaction.response.send_message("❌ Anexe a print do comprovante de pagamento primeiro!", ephemeral=True)
            return
        
        modal = PagamentoFarmModal(self.user_id, self.user_name, interaction.channel, imagem_url)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Fechar Caixa", style=discord.ButtonStyle.danger, emoji="📊", row=2)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        modal = FechamentoCaixaModal(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=2)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        modal = MudarNomeModal(interaction.channel)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=2)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        fechamentos = dados["caixa_semana"].get(str(self.user_id), [])
        
        if not fechamentos:
            await interaction.response.send_message("Nenhum fechamento registrado.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="HISTÓRICO DE CAIXA",
            description=f"Últimos {min(10, len(fechamentos))} registros",
            color=discord.Color.blue()
        )
        
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            embed.add_field(
                name=f"📅 {data}",
                value=f"Farm Sujo: R$ {fech['farm_sujo']:,.2f}\n"
                      f"Salário: R$ {fech['salario']:,.2f}\n"
                      f"Extra: R$ {fech['extra']:,.2f}\n"
                      f"**Pago: R$ {fech['valor_pago']:,.2f}**\n"
                      f"Admin: {fech['admin']}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=3)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True)
            return
        
        view = ConfirmarFechamentoView(self.user_id, interaction.channel)
        await interaction.response.send_message("⚠️ Tem certeza? Os registros serão mantidos.", view=view, ephemeral=True)

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
        
        await log_acao("fechar_canal", interaction.user, f"Canal {nome_canal} fechado", 0xff0000)
        await log_admin("CANAL FECHADO", f"Canal: {nome_canal}\nDono: {user.mention if user else 'Desconhecido'}", 0xff0000)
    
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Cancelado!", ephemeral=True)

# ========= MODAIS ADMIN PARA PAINEL =========
class RemoverUsuarioModal(Modal, title="Remover Usuário do Sistema"):
    user_id = TextInput(
        label="ID do usuário",
        placeholder="Digite o ID do usuário",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        try:
            user_id = int(self.user_id.value.strip())
            user = await interaction.client.fetch_user(user_id)
            
            if str(user_id) in dados["usuarios_banidos"]:
                await interaction.followup.send("Usuário já foi removido!", ephemeral=True)
                return
            
            total_limpo = await limpar_logs_usuario(user_id, user.name)
            
            await interaction.followup.send(f"✅ Usuário {user.mention} removido do sistema!\n**Mensagens anonimizadas:** {total_limpo}", ephemeral=True)
            await log_admin("USUÁRIO REMOVIDO", f"Usuário: {user.mention}\nAdmin: {interaction.user.mention}\nMensagens limpas: {total_limpo}", 0xff0000)
            await atualizar_ranking()
            
            if interaction.guild:
                member = interaction.guild.get_member(user_id)
                if member:
                    cargo_admin = interaction.guild.get_role(CARGO_ADMIN_ID)
                    if cargo_admin and cargo_admin in member.roles:
                        await member.remove_roles(cargo_admin)
            
        except Exception as e:
            await interaction.followup.send(f"Erro: {e}", ephemeral=True)

class BackupView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Criar Backup", style=discord.ButtonStyle.success, emoji="💾")
    async def criar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        backup_nome = f"backup_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        backup = {
            "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name,
            "dados": dados.copy()
        }
        
        with open(backup_nome, "w", encoding="utf-8") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)
        
        await criar_canal_backup("novo", backup_nome)
        await interaction.followup.send("Backup criado com sucesso!", ephemeral=True)
        await log_admin("BACKUP CRIADO", f"Admin: {interaction.user.mention}\nArquivo: {backup_nome}", 0x00ff00)
    
    @discord.ui.button(label="Apagar Backups", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def apagar_backups(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        backups_encontrados = []
        for arquivo in os.listdir('.'):
            if arquivo.startswith('backup_') and arquivo.endswith('.json'):
                backups_encontrados.append(arquivo)
        
        if not backups_encontrados:
            await interaction.followup.send("Nenhum backup encontrado!", ephemeral=True)
            return
        
        for backup in backups_encontrados:
            await criar_canal_backup("deletado", backup)
            os.remove(backup)
        
        await interaction.followup.send(f"{len(backups_encontrados)} backup(s) deletado(s)!", ephemeral=True)
        await log_admin("BACKUPS DELETADOS", f"Admin: {interaction.user.mention}\nQuantidade: {len(backups_encontrados)}", 0xff0000)

class AdminPanelCategoriaView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Adicionar Admin", style=discord.ButtonStyle.danger, emoji="👑")
    async def add_admin(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        modal = AdicionarAdminModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remover Admin", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove_admin(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        modal = RemoverAdminModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Remover Usuário", style=discord.ButtonStyle.danger, emoji="👤❌")
    async def remover_usuario(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        modal = RemoverUsuarioModal()
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Gerenciar Backups", style=discord.ButtonStyle.primary, emoji="💾")
    async def gerenciar_backups(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
            return
        
        view = BackupView()
        embed = discord.Embed(
            title="GERENCIAR BACKUPS",
            description="Escolha uma opção abaixo:\n\n"
                       "• **Criar Backup** - Salva todos os dados atuais\n"
                       "• **Apagar Backups** - Remove todos os arquivos de backup",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AdicionarAdminModal(Modal, title="Adicionar Administrador"):
    identificador = TextInput(
        label="ID ou Nome do usuário",
        placeholder="Digite o ID ou @nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
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
            await interaction.followup.send("Usuário não encontrado!", ephemeral=True)
            return
        
        if str(usuario_alvo.id) in dados["admins"]:
            await interaction.followup.send(f"{usuario_alvo.mention} já é admin!", ephemeral=True)
            return
        
        dados["admins"].append(str(usuario_alvo.id))
        salvar_dados()
        
        if interaction.guild:
            cargo_admin = interaction.guild.get_role(CARGO_ADMIN_ID)
            if cargo_admin:
                member = interaction.guild.get_member(usuario_alvo.id)
                if member:
                    try:
                        await member.add_roles(cargo_admin)
                    except:
                        pass
        
        await interaction.followup.send(f"{usuario_alvo.mention} agora é administrador!", ephemeral=True)
        await log_acao("setar_admin", interaction.user, f"Novo admin: {usuario_alvo.mention}", 0x9b59b6)

class RemoverAdminModal(Modal, title="Remover Administrador"):
    identificador = TextInput(
        label="ID ou Nome do usuário",
        placeholder="Digite o ID ou @nome",
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Sem permissão!", ephemeral=True)
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
            await interaction.followup.send("Usuário não encontrado!", ephemeral=True)
            return
        
        if str(usuario_alvo.id) not in dados["admins"]:
            await interaction.followup.send(f"{usuario_alvo.mention} não é admin!", ephemeral=True)
            return
        
        dados["admins"].remove(str(usuario_alvo.id))
        salvar_dados()
        
        if interaction.guild:
            cargo_admin = interaction.guild.get_role(CARGO_ADMIN_ID)
            if cargo_admin:
                member = interaction.guild.get_member(usuario_alvo.id)
                if member and cargo_admin in member.roles:
                    try:
                        await member.remove_roles(cargo_admin)
                    except:
                        pass
        
        await interaction.followup.send(f"{usuario_alvo.mention} não é mais administrador!", ephemeral=True)
        await log_acao("setar_admin", interaction.user, f"Admin removido: {usuario_alvo.mention}", 0xff0000)

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
            await interaction.response.send_message("Bot precisa de permissão de Administrador.", ephemeral=True)
            return
        
        if str(interaction.user.id) in dados["canais"]:
            canal_id = dados["canais"][str(interaction.user.id)]
            canal = interaction.guild.get_channel(canal_id)
            if canal:
                await interaction.response.send_message(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True)
                return
            else:
                del dados["canais"][str(interaction.user.id)]
                salvar_dados()
        
        await interaction.response.send_message("🔄 Criando seu canal...", ephemeral=True)
        
        try:
            categoria_farms = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria_farms or not isinstance(categoria_farms, discord.CategoryChannel):
                await interaction.edit_original_response(content="Erro: Categoria não encontrada!")
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
            
            nome_canal = f"farm-{interaction.user.name}".lower().replace(" ", "-")[:90]
            canal = await categoria_farms.create_text_channel(nome_canal, overwrites=overwrites)
            
            dados["canais"][str(interaction.user.id)] = canal.id
            salvar_dados()
            
            # Verificar se o usuário que está criando é admin
            if is_admin(interaction.user):
                view = FarmChannelViewAdmin(interaction.user.id, interaction.user.name, canal.id)
                tipo_view = "ADMIN"
            else:
                view = FarmChannelViewMembro(interaction.user.id, interaction.user.name, canal.id)
                tipo_view = "MEMBRO"
            
            embed = discord.Embed(
                title="SEU CANAL PRIVADO",
                description=f"Bem-vindo(a) {interaction.user.mention}!\n\n"
                           "Este é seu canal exclusivo para farms.\n"
                           "🔒 Apenas você e administradores têm acesso.\n\n"
                           f"**BOTÕES DISPONÍVEIS PARA {tipo_view}:**\n"
                           "📦 **Farm Produtos** - Registrar farm de produtos (com print)\n"
                           "💰 **Farm Dinheiro Sujo** - Registrar dinheiro sujo (com print)",
                color=discord.Color.green()
            )
            
            if tipo_view == "ADMIN":
                embed.description += "\n\n**BOTÕES ADMINISTRATIVOS:**\n"
                embed.description += "📊 **Meu Histórico** - Ver farms\n"
                embed.description += "💰 **Meus Pagamentos** - Ver valores recebidos\n"
                embed.description += "💰 **Registrar Pagamento** - Pagar membro\n"
                embed.description += "📊 **Fechar Caixa** - Fechar caixa semanal\n"
                embed.description += "✏️ **Mudar Nome** - Renomear canal\n"
                embed.description += "📜 **Histórico Caixa** - Ver fechamentos\n"
                embed.description += "🗑️ **Fechar Canal** - Deletar canal"
            
            await canal.send(embed=embed, view=view)
            
            await log_acao("criar_canal", interaction.user, f"Canal criado: {canal.mention}", 0x00ff00)
            await interaction.edit_original_response(content=f"✅ Canal criado! Acesse: {canal.mention}")
            await atualizar_ranking()
            
        except Exception as e:
            await interaction.edit_original_response(content=f"Erro: {str(e)[:200]}")

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    print(f"Usuário {member.name} ({member.id}) saiu do servidor!")
    
    if str(member.id) in dados["usuarios_banidos"]:
        return
    
    await log_admin("USUÁRIO SAIU", f"Usuário: {member.mention}\nID: {member.id}\nIniciando limpeza...", 0xffa500)
    await limpar_logs_usuario(member.id, member.name)
    
    if str(member.id) in dados["canais"]:
        canal_id = dados["canais"][str(member.id)]
        canal = member.guild.get_channel(canal_id)
        if canal:
            try:
                await canal.delete(reason=f"Usuário {member.name} saiu do servidor")
                await log_admin("CANAL REMOVIDO", f"Usuário: {member.mention}\nCanal: #{canal.name}", 0xff0000)
            except:
                pass
        del dados["canais"][str(member.id)]
        salvar_dados()
    
    await log_admin("LIMPEZA CONCLUÍDA", f"Usuário {member.mention} removido do sistema.", 0x00ff00)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} está online!")
    print(f"Conectado a {len(bot.guilds)} servidores")
    
    for guild in bot.guilds:
        print(f"\nServidor: {guild.name}")
        
        # Verificar cargos
        cargo_admin = guild.get_role(CARGO_ADMIN_ID)
        if cargo_admin:
            print(f"  ✅ Cargo Admin encontrado: {cargo_admin.name}")
        else:
            print(f"  ⚠️ Cargo Admin ID {CARGO_ADMIN_ID} não encontrado!")
        
        # Canal de compra e venda
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas and isinstance(canal_vendas, discord.TextChannel):
            async for msg in canal_vendas.history(limit=10):
                if msg.author == bot.user:
                    await msg.delete()
            
            embed_vendas = discord.Embed(
                title="SISTEMA DE COMPRA E VENDA",
                description="Clique nos botões abaixo para registrar:\n\n"
                           "💸 **Venda de Munição**\n"
                           "🛒 **Compra de Produto**",
                color=discord.Color.blue()
            )
            view_vendas = CompraVendaView()
            await canal_vendas.send(embed=embed_vendas, view=view_vendas)
            print(f"  ✅ Canal de compra/venda configurado!")
        else:
            print(f"  ⚠️ Canal de compra/venda ID {CHAT_COMPRA_VENDA_ID} não encontrado!")
        
        # Canal de criar canal
        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel and isinstance(categoria_painel, discord.CategoryChannel):
            canal_criar = None
            for channel in categoria_painel.channels:
                if channel.name == "criar-canal" and isinstance(channel, discord.TextChannel):
                    canal_criar = channel
                    break
            
            if not canal_criar:
                canal_criar = await categoria_painel.create_text_channel("criar-canal")
                print(f"  ✅ Canal 'criar-canal' criado!")
            
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            
            embed = discord.Embed(
                title="SISTEMA DE FARM",
                description="Clique no botão abaixo para criar seu canal privado!\n\n🔒 Apenas você e os administradores terão acesso",
                color=discord.Color.blue()
            )
            view = BotaoCriarCanalView()
            await canal_criar.send(embed=embed, view=view)
            print(f"  ✅ Painel de criação configurado!")
        else:
            print(f"  ⚠️ Categoria do painel ID {CATEGORIA_PAINEL_ID} não encontrada!")
        
        # Painel de Backup na categoria de backup
        categoria_backup = guild.get_channel(CATEGORIA_BACKUP_ID)
        if categoria_backup and isinstance(categoria_backup, discord.CategoryChannel):
            canal_backup_painel = None
            for channel in categoria_backup.channels:
                if channel.name == "painel-backup" and isinstance(channel, discord.TextChannel):
                    canal_backup_painel = channel
                    break
            
            if not canal_backup_painel:
                canal_backup_painel = await categoria_backup.create_text_channel("painel-backup")
                print(f"  ✅ Canal 'painel-backup' criado!")
            
            async for msg in canal_backup_painel.history(limit=5):
                if msg.author == bot.user:
                    await msg.delete()
            
            embed_backup = discord.Embed(
                title="💾 PAINEL DE BACKUP",
                description="**BOTÕES DISPONÍVEIS:**\n\n"
                           "💾 **Criar Backup** - Salva todos os dados atuais em um novo canal\n"
                           "🗑️ **Apagar Backups** - Remove todos os backups antigos",
                color=discord.Color.blue()
            )
            view_backup = BackupView()
            await canal_backup_painel.send(embed=embed_backup, view=view_backup)
            print(f"  ✅ Painel de backup configurado!")
        else:
            print(f"  ⚠️ Categoria de backup ID {CATEGORIA_BACKUP_ID} não encontrada!")
        
        # ========= PAINEL ADMIN NO CHAT ESPECÍFICO =========
        # Usar o canal específico do painel admin
        canal_admin_painel = bot.get_channel(CHAT_ADMIN_PAINEL_ID)
        
        if canal_admin_painel and isinstance(canal_admin_painel, discord.TextChannel):
            # Verificar se o canal está na categoria correta
            if canal_admin_painel.category_id == CATEGORIA_ADMIN_PAINEL_ID:
                # Limpar mensagens antigas do bot
                async for msg in canal_admin_painel.history(limit=10):
                    if msg.author == bot.user:
                        await msg.delete()
                
                embed_admin = discord.Embed(
                    title="👑 PAINEL ADMINISTRATIVO",
                    description="**BOTÕES DISPONÍVEIS:**\n\n"
                               "👑 **Adicionar Admin** - Dá cargo de administrador para um usuário\n"
                               "🗑️ **Remover Admin** - Remove cargo de administrador\n"
                               "👤❌ **Remover Usuário** - Remove um usuário do sistema e apaga todas as menções\n"
                               "💾 **Gerenciar Backups** - Criar ou apagar backups do sistema",
                    color=discord.Color.purple()
                )
                view_admin = AdminPanelCategoriaView()
                await canal_admin_painel.send(embed=embed_admin, view=view_admin)
                print(f"  ✅ Painel administrativo configurado no canal #{canal_admin_painel.name}!")
            else:
                print(f"  ⚠️ Canal {canal_admin_painel.name} não está na categoria correta!")
        else:
            print(f"  ⚠️ Canal de Admin ID {CHAT_ADMIN_PAINEL_ID} não encontrado!")
    
    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x00ff00)
    print(f"\n🚀 BOT PRONTO!")

# ========= INICIAR =========
if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)