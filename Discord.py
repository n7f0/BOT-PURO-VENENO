import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, TextInput, UserSelect, Select
import asyncio
from datetime import datetime
import json
import os
import sys
import aiohttp
import re
import glob

# ========= CONFIGURAÇÕES =========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    sys.exit(1)

CARGO_ADMIN_GERAL_ID = int(os.getenv("CARGO_ADMIN_GERAL_ID", "1386002307950317759"))
CARGO_MEMBRO_ID = int(os.getenv("CARGO_MEMBRO_ID", "1386004220691353675"))
CARGO_COMPRA_VENDA_IDS = [
    1386002307950317759,
    1386002372504850573,
    1386002443397234818,
    1386004129310179362
]
CARGO_REGISTRAR_ACAO_IDS = [
    1386002307950317759,
    1386002372504850573,
    1386002443397234818,
    1386004021659172914,
    1386004190026792991
]

CATEGORIA_FARMS_ID = int(os.getenv("CATEGORIA_FARMS_ID", "1498108914703532183"))
CATEGORIA_PAINEL_ID = int(os.getenv("CATEGORIA_PAINEL_ID", "1498111045489790987"))
CATEGORIA_BACKUP_ID = int(os.getenv("CATEGORIA_BACKUP_ID", "1498305209175380080"))
CATEGORIA_COMPRA_VENDA_LOGS_ID = int(os.getenv("CATEGORIA_COMPRA_VENDA_LOGS_ID", "1498305956235448390"))
CHAT_LOGS_ID = int(os.getenv("CHAT_LOGS_ID", "1498109309622550638"))
CHAT_ADMIN_LOGS_ID = int(os.getenv("CHAT_ADMIN_LOGS_ID", "1498109569853816963"))
CHAT_RANK_ID = int(os.getenv("CHAT_RANK_ID", "1498109956421976124"))
CHAT_COMPRA_VENDA_ID = int(os.getenv("CHAT_COMPRA_VENDA_ID", "1498110154317496330"))
LOG_REGISTROS_ID = int(os.getenv("LOG_REGISTROS_ID", "1498349960062570740"))
CANAL_LIVES_PAINEL_ID = int(os.getenv("CANAL_LIVES_PAINEL_ID", "1498692536800252084"))
CANAL_ACOES_PAINEL_ID = int(os.getenv("CANAL_ACOES_PAINEL_ID", "1498714657970589717"))
CANAL_ACOES_LOGS_ID = int(os.getenv("CANAL_ACOES_LOGS_ID", "1498718200173433002"))
CANAL_BACKUP_ARQUIVOS_ID = int(os.getenv("CANAL_BACKUP_ARQUIVOS_ID", "1498898858413920386"))

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# ========= BANCO DE DADOS =========
dados = {
    "usuarios": {},
    "canais": {},
    "admins": [],
    "config": {},
    "caixa_semana": {},
    "compras_vendas": [],
    "usuarios_banidos": [],
    "dinheiro_sujo": {},
    "lives": {
        "config": {},
        "streamers": {},
        "last_notified": {},
        "status": {}
    },
    "acoes": {}
}

def salvar_dados():
    with open("dados_bot.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_dados():
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            loaded = json.load(f)
            dados.update(loaded)
        return True
    except:
        return False

async def salvar_backup_completo(admin_name="Sistema"):
    backup_nome = f"backup_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup = {
        "data_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "admin": admin_name,
        "dados": json.loads(json.dumps(dados))
    }
    with open(backup_nome, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)
    salvar_dados()
    canal_backup = bot.get_channel(CANAL_BACKUP_ARQUIVOS_ID)
    if canal_backup and isinstance(canal_backup, discord.TextChannel):
        embed = discord.Embed(
            title="💾 BACKUP COMPLETO SALVO",
            description=f"**Arquivo:** {backup_nome}\n**Data:** {backup['data_backup']}\n**Admin:** {admin_name}",
            color=discord.Color.green()
        )
        await canal_backup.send(embed=embed)
        await canal_backup.send(file=discord.File(backup_nome))
        if os.path.exists("dados_bot.json"):
            await canal_backup.send(file=discord.File("dados_bot.json"))
    return backup_nome

async def criar_canal_backup(tipo, nome_arquivo=None):
    categoria = bot.get_channel(CATEGORIA_BACKUP_ID)
    if not categoria: return None
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    if tipo == "novo":
        canal = await categoria.create_text_channel(f"backup-novo-{data}")
        embed = discord.Embed(title="NOVO BACKUP CRIADO", description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", color=discord.Color.green())
        await canal.send(embed=embed)
        if nome_arquivo and os.path.exists(nome_arquivo):
            await canal.send(file=discord.File(nome_arquivo))
        return canal
    elif tipo == "deletado":
        canal = await categoria.create_text_channel(f"backup-deletado-{data}")
        embed = discord.Embed(title="BACKUP DELETADO", description=f"**Arquivo:** {nome_arquivo}\n**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", color=discord.Color.red())
        await canal.send(embed=embed)
        return canal

async def criar_canal_compra_venda_log(tipo, dados_log):
    categoria = bot.get_channel(CATEGORIA_COMPRA_VENDA_LOGS_ID)
    if not categoria: return None
    data = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    canal = await categoria.create_text_channel(f"log-{tipo}-{data}")
    embed = discord.Embed(title=f"LOG DE {tipo.upper()}", color=discord.Color.blue(), timestamp=datetime.now())
    for chave, valor in dados_log.items():
        embed.add_field(name=chave, value=valor, inline=False)
    await canal.send(embed=embed)
    return canal

async def limpar_logs_usuario(user_id, user_name):
    if str(user_id) in dados["usuarios_banidos"]: return 0
    dados["usuarios_banidos"].append(str(user_id))
    total_limpo = 0
    for canal_id in [CHAT_LOGS_ID, CHAT_ADMIN_LOGS_ID, CHAT_RANK_ID, CHAT_COMPRA_VENDA_ID]:
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try: await mensagem.edit(content=novo); total_limpo += 1
                        except: pass
    for canal_id in dados["canais"].values():
        canal = bot.get_channel(canal_id)
        if canal:
            async for mensagem in canal.history(limit=None):
                if mensagem.author == bot.user:
                    if f"<@{user_id}>" in mensagem.content or f"<@!{user_id}>" in mensagem.content:
                        novo = mensagem.content.replace(f"<@{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]").replace(f"<@!{user_id}>", f"[USUÁRIO REMOVIDO - {user_name}]")
                        try: await mensagem.edit(content=novo); total_limpo += 1
                        except: pass
    if str(user_id) in dados["usuarios"]:
        dados["usuarios"][str(user_id)] = {"farms":[],"pagamentos":[],"dinheiro_sujo":0,"nome":f"[REMOVIDO - {user_name}]","removido_em":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"removido_por":"sistema","transacoes_dinheiro_sujo":[]}
        salvar_dados()
    if str(user_id) in dados["canais"]:
        canal = bot.get_channel(dados["canais"][str(user_id)])
        if canal:
            try: await canal.delete(reason=f"Usuário {user_name} removido do sistema")
            except: pass
        del dados["canais"][str(user_id)]
        salvar_dados()
    return total_limpo

async def log_acao(acao, usuario, detalhes, cor=None):
    cores = {"criar_canal":0x00ff00,"registrar_farm":0x00ff00,"registrar_dinheiro_sujo":0xff0000,"pagar":0xffa500,"fechar_canal":0xff0000,"fechar_caixa":0xffa500,"reset_rank":0xff0000,"info":0x3498db,"admin":0x9b59b6,"setar_admin":0x9b59b6,"compra_venda":0x00ff00,"usuario_removido":0xff0000,"editar_farm":0x3498db,"editar_dinheiro_sujo":0x3498db}
    cor_final = cores.get(acao, 0x3498db) if cor is None else cor
    canal_logs = bot.get_channel(CHAT_LOGS_ID)
    if canal_logs:
        embed = discord.Embed(title=f"LOG: {acao.upper()}", description=detalhes, color=cor_final, timestamp=datetime.now())
        if usuario: embed.set_author(name=usuario.name, icon_url=usuario.display_avatar.url)
        else: embed.set_author(name="Sistema")
        await canal_logs.send(embed=embed)

async def log_admin(titulo, descricao, cor=0xffa500):
    canal = bot.get_channel(CHAT_ADMIN_LOGS_ID)
    if canal:
        await canal.send(embed=discord.Embed(title=titulo, description=descricao, color=cor, timestamp=datetime.now()))

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

def tem_cargo(member, cargos_ids):
    if not hasattr(member, 'guild'): return False
    for cid in cargos_ids:
        cargo = member.guild.get_role(cid)
        if cargo and cargo in member.roles: return True
    return False

def is_admin(member) -> bool: return tem_cargo(member, [CARGO_ADMIN_GERAL_ID])
def is_membro(member) -> bool: return tem_cargo(member, [CARGO_MEMBRO_ID])
def pode_comprar_vender(member) -> bool: return tem_cargo(member, CARGO_COMPRA_VENDA_IDS)
def pode_registrar_acao(member) -> bool: return tem_cargo(member, CARGO_REGISTRAR_ACAO_IDS)

async def atualizar_ranking():
    canal = bot.get_channel(CHAT_RANK_ID)
    if not canal: return
    async for msg in canal.history(limit=50):
        if msg.author == bot.user: await msg.delete()
    usuarios_data = []
    for uid, data in dados["usuarios"].items():
        if "removido_em" in data: continue
        try:
            user = await bot.fetch_user(int(uid))
            tot_chumbo = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="CHUMBO")
            tot_capsula = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="CAPSULA")
            tot_polvora = sum(p["quantidade"] for f in data["farms"] for p in f.get("produtos",[]) if p["produto"]=="POLVORA")
            tot_pag = sum(p["valor"] for p in data["pagamentos"]); qtd_pag = len(data["pagamentos"]); din_sujo = data.get("dinheiro_sujo",0)
            usuarios_data.append({"nome":user.name,"user_id":uid,"total_chumbo":tot_chumbo,"total_capsula":tot_capsula,"total_polvora":tot_polvora,"total_pagamentos":tot_pag,"quantidade_pagamentos":qtd_pag,"dinheiro_sujo":din_sujo})
        except: continue
    emb = discord.Embed(title="RANKING GERAL", description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", color=discord.Color.gold())
    for nome, key in [("CHUMBO","total_chumbo"),("CAPSULA","total_capsula"),("POLVORA","total_polvora")]:
        lista = sorted(usuarios_data, key=lambda x: x[key], reverse=True)[:5]
        txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - {u[key]:,} itens\n" for i,u in enumerate(lista,1) if u[key]>0]
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)
    lista_salario = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:5]
    txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pagamentos)\n" for i,u in enumerate(lista_salario,1) if u["total_pagamentos"]>0]
    emb.add_field(name="TOP SALÁRIO", value=txt or "Nenhum dado ainda", inline=False)
    lista_sujo = sorted(usuarios_data, key=lambda x: x["dinheiro_sujo"], reverse=True)[:5]
    txt = ""; [txt := txt + f"{'🥇' if i==1 else '🥈' if i==2 else '🥉' if i==3 else f'{i}°'} **{u['nome']}** - R$ {u['dinheiro_sujo']:,.2f}\n" for i,u in enumerate(lista_sujo,1) if u["dinheiro_sujo"]>0]
    emb.add_field(name="DINHEIRO SUJO", value=txt or "Nenhum dado ainda", inline=False)
    await canal.send(embed=emb, view=RankingView())

class RankingView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.primary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(); await atualizar_ranking(); await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas o cargo Administrador Geral pode resetar o ranking.", ephemeral=True); return
        await interaction.response.send_message("⚠️ ATENÇÃO! ...", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self): super().__init__(timeout=60)
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await salvar_backup_completo(interaction.user.name)
        dados["usuarios"] = {}; dados["caixa_semana"] = {}; dados["dinheiro_sujo"] = {}; salvar_dados()
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0xff0000)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0xff0000)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True); await atualizar_ranking(); self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button): await interaction.response.send_message("Reset cancelado.", ephemeral=True); self.stop()

# ========= MODAIS DE FARM =========
class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    quantidade = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not (is_admin(interaction.user) or is_membro(interaction.user)):
            await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: valor = float(self.quantidade.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[]}
        if "transacoes_dinheiro_sujo" not in dados["usuarios"][str(self.user_id)]:
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
        transacao = {"valor": valor,"data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url": imagem_url,"registrado_por": interaction.user.id}
        dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"].append(transacao)
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = sum(t["valor"] for t in dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(title="💰 DINHEIRO SUJO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Registrado por:** {interaction.user.mention}", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"R$ {valor:,.2f} registrado como dinheiro sujo para {self.user_name}!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xff0000); await atualizar_ranking()

class FarmProdutosModal(Modal, title="Registrar Farm Produtos"):
    chumbo = TextInput(label="CHUMBO - Quantidade", placeholder="Ex: 250", required=False)
    capsula = TextInput(label="CAPSULA - Quantidade", placeholder="Ex: 150", required=False)
    polvora = TextInput(label="POLVORA - Quantidade", placeholder="Ex: 300", required=False)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        produtos = []
        for campo, nome in [(self.chumbo,"CHUMBO"),(self.capsula,"CAPSULA"),(self.polvora,"POLVORA")]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd>0: produtos.append({"produto":nome,"quantidade":qtd})
                except ValueError: pass
        if not produtos: await interaction.followup.send("Nenhum produto válido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print da farm** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[]}
        old_chumbo = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        old_capsula = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        old_polvora = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        registro = {"produtos":produtos,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url,"validado":True,"farm_id":len(dados["usuarios"][str(self.user_id)]["farms"])+1}
        dados["usuarios"][str(self.user_id)]["farms"].append(registro); salvar_dados()
        new_chumbo = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        new_capsula = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        new_polvora = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        canal_user = bot.get_channel(dados["canais"].get(str(self.user_id)))
        if canal_user:
            for nome, old, new in [("CHUMBO",old_chumbo,new_chumbo), ("CAPSULA",old_capsula,new_capsula), ("POLVORA",old_polvora,new_polvora)]:
                if new // 600 > old // 600: await canal_user.send(f"🎉 **Parabéns! Você bateu a meta de 600 {nome}!**\nTotal acumulado: {new}. Continue assim!")
        embed = discord.Embed(title="FARM PRODUTOS REGISTRADA COM SUCESSO", description=f"**Usuário:** <@{self.user_id}>\n", color=discord.Color.green())
        desc = "".join(f"🔫 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos); embed.description += desc
        embed.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)
        produtos_str = ', '.join(f"{p['produto']}: {p['quantidade']}" for p in produtos)
        await log_acao("registrar_farm", interaction.user, f"Produtos: {produtos_str}")
        await log_admin("NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {produtos_str}", 0x00ff00); await atualizar_ranking()

class PagamentoFarmModal(Modal, title="Registrar Pagamento"):
    valor = TextInput(label="Valor do Pagamento (R$)", placeholder="Ex: 500", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores podem registrar pagamentos.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: valor = float(self.valor.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[]}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({"valor":valor,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.id,"admin_nome":interaction.user.name,"tipo":"Pagamento","print_url":imagem_url}); salvar_dados()
        try: await (await interaction.client.fetch_user(int(self.user_id))).send(embed=discord.Embed(title="PAGAMENTO RECEBIDO", description=f"Você recebeu R$ {valor:,.2f}!", color=discord.Color.green()).set_image(url=imagem_url))
        except: pass
        embed = discord.Embed(title="PAGAMENTO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}", color=discord.Color.green(), timestamp=datetime.now()).set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {valor:,.2f} registrado!", ephemeral=True)
        await log_acao("pagar", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xffa500); await atualizar_ranking()

class FechamentoSummaryView(View):
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__(timeout=300); self.user_id = user_id; self.user_name = user_name; self.canal = canal
        self.total_sujo = total_sujo; self.lavagem = lavagem; self.faccao = faccao; self.membro_base = membro_base
    @discord.ui.button(label="Continuar Fechamento", style=discord.ButtonStyle.success, emoji="✅")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        modal = FechamentoCaixaModal(self.user_id, self.user_name, self.canal, self.total_sujo, self.lavagem, self.faccao, self.membro_base)
        await interaction.response.send_modal(modal)

class FechamentoCaixaModal(Modal, title="Finalizar Fechamento"):
    meta_farm = TextInput(label="Meta de Farm (Sim/Não)", placeholder="Digite Sim ou Não", required=True)
    bonus = TextInput(label="Bônus (R$) - Opcional", placeholder="Ex: 500 (deixe 0 se não houver)", required=False, default="0")
    observacao = TextInput(label="Observação (mensagem carinhosa)", placeholder="Deixe uma mensagem para o usuário...", required=False, style=discord.TextStyle.long)
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
        self.total_sujo = total_sujo; self.lavagem = lavagem; self.faccao = faccao; self.membro_base = membro_base
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        meta = self.meta_farm.value.strip().lower()
        if meta not in ["sim","não","nao"]: await interaction.followup.send("Meta deve ser Sim/Não!", ephemeral=True); return
        meta = "Sim" if meta=="sim" else "Não"
        bonus_str = self.bonus.value.strip() or "0"
        try: bonus_valor = float(bonus_str.replace(",","."))
        except ValueError: await interaction.followup.send("Bônus inválido!", ephemeral=True); return
        obs = self.observacao.value.strip() if self.observacao.value else None
        pagamento_final = self.membro_base + bonus_valor
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0,"transacoes_dinheiro_sujo":[]}
        user_data = dados["usuarios"][str(self.user_id)]
        if pagamento_final > 0:
            user_data["pagamentos"].append({"valor":pagamento_final,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.id,"admin_nome":interaction.user.name,"tipo":"Fechamento de Caixa Semanal","detalhes":{"total_sujo":self.total_sujo,"lavagem":self.lavagem,"faccao":self.faccao,"membro_base":self.membro_base,"bonus":bonus_valor},"print_url":imagem_url})
        tot_chumbo = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        tot_capsula = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        tot_polvora = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        fechamento = {"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.name,"admin_id":interaction.user.id,"usuario":self.user_name,"usuario_id":self.user_id,"meta_farm":meta,"produtos":{"chumbo":tot_chumbo,"capsula":tot_capsula,"polvora":tot_polvora},"dinheiro_sujo":{"total":self.total_sujo,"lavagem":self.lavagem,"faccao":self.faccao,"membro_base":self.membro_base,"bonus":bonus_valor,"pago":pagamento_final},"print_url":imagem_url,"observacao":obs}
        if str(self.user_id) not in dados["caixa_semana"]: dados["caixa_semana"][str(self.user_id)] = []
        dados["caixa_semana"][str(self.user_id)].append(fechamento); salvar_dados()
        embed = discord.Embed(title="FECHAMENTO DE CAIXA SEMANAL", description=f"**{self.user_name}** fechou a semana!", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Meta de Farm", value=meta, inline=False)
        if tot_chumbo>0 or tot_capsula>0 or tot_polvora>0: embed.add_field(name="Produtos", value=f"🔫 Chumbo: {tot_chumbo}\n💣 Cápsula: {tot_capsula}\n💥 Pólvora: {tot_polvora}", inline=False)
        embed.add_field(name="Total Farmado", value=f"R$ {self.total_sujo:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {self.lavagem:,.2f}", inline=True)
        embed.add_field(name="Facção (60%)", value=f"R$ {self.faccao:,.2f}", inline=True)
        embed.add_field(name="Membro Base (40%)", value=f"R$ {self.membro_base:,.2f}", inline=True)
        if bonus_valor > 0: embed.add_field(name="Bônus", value=f"R$ {bonus_valor:,.2f}", inline=True)
        embed.add_field(name="💰 Pagamento Final", value=f"R$ {pagamento_final:,.2f}", inline=False)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        if obs: embed.add_field(name="💌 Mensagem", value=obs, inline=False)
        embed.set_image(url=imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {pagamento_final:,.2f} registrado!", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nPagamento: R$ {pagamento_final}", 0xffa500); await atualizar_ranking()

# ========= COMPRA/VENDA =========
class VendaModal(Modal, title="Venda de Munição"):
    tipo_municao = TextInput(label="Tipo de Munição (PISTOLA/SUB/RIFLE/FUZIL)", placeholder="Ex: PISTOLA", required=True)
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_compradora = TextInput(label="Facção Compradora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Venda", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_comprar_vender(interaction.user): await interaction.response.send_message("Você não tem permissão para registrar vendas.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        tipo = self.tipo_municao.value.strip().upper()
        if tipo not in ["PISTOLA","SUB","RIFLE","FUZIL"]: await interaction.followup.send("Tipo de munição inválido! Use PISTOLA, SUB, RIFLE ou FUZIL.", ephemeral=True); return
        try: qtd = int(self.quantidade.value); valor = float(self.valor_total.value.replace(",","."))
        except ValueError: await interaction.followup.send("Quantidade ou valor inválidos!", ephemeral=True); return
        faccao = self.faccao_compradora.value.strip(); responsavel_nome = self.responsavel.value.strip()
        await interaction.followup.send("📸 Agora envie a **print do comprovante da venda**.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        dados_log = {"Tipo":"VENDA","Munição":tipo,"Quantidade":f"{qtd:,} unidades","Valor Total":f"R$ {valor:,.2f}","Facção Compradora":faccao,"Responsável":responsavel_nome,"Registrado por":interaction.user.mention}
        await criar_canal_compra_venda_log("venda", dados_log)
        dados["compras_vendas"].append({"tipo":"venda","municao":tipo,"quantidade":qtd,"valor_total":valor,"faccao_compradora":faccao,"responsavel":responsavel_nome,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url}); salvar_dados()
        await interaction.followup.send(f"✅ Venda de **{qtd:,} {tipo}** para **{faccao}** registrada! Valor: R$ {valor:,.2f}", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Venda: {qtd} {tipo} - R$ {valor} - {faccao}", 0x00ff00)

class CompraModal(Modal, title="Compra de Produto"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not pode_comprar_vender(interaction.user): await interaction.response.send_message("Você não tem permissão para registrar compras.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value); valor = float(self.valor_total.value.replace(",","."))
        except: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante da compra**.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==interaction.channel and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        await criar_canal_compra_venda_log("compra", {"Tipo":"COMPRA","Quantidade":f"{qtd:,}","Produto":self.produto.value,"Valor Total":f"R$ {valor:,.2f}","Facção Vendedora":self.faccao_vendedora.value,"Responsável":self.responsavel.value,"Registrado por":interaction.user.mention})
        dados["compras_vendas"].append({"tipo":"compra","quantidade":qtd,"produto":self.produto.value,"valor_total":valor,"faccao_vendedora":self.faccao_vendedora.value,"responsavel":self.responsavel.value,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url}); salvar_dados()
        await interaction.followup.send("Compra registrada!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Compra: {qtd} x {self.produto.value} - R$ {valor}", 0x00ff00)

class CompraVendaView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Venda de Munição", style=discord.ButtonStyle.success, emoji="💸")
    async def venda(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(VendaModal())
    @discord.ui.button(label="Compra de Produto", style=discord.ButtonStyle.primary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(CompraModal())

# ========= VIEW DO CANAL PRIVADO =========
class MudarNomeModal(Modal, title="Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", placeholder="Ex: farm-lucas", required=True, max_length=90)
    def __init__(self, canal): super().__init__(); self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = ''.join(c for c in self.novo_nome.value.lower().replace(" ","-") if c.isalnum() or c=='-') or "farm"
        try: await self.canal.edit(name=nome); await interaction.followup.send(f"Nome alterado para {nome}", ephemeral=True)
        except Exception as e: await interaction.followup.send(f"Erro: {str(e)[:100]}", ephemeral=True)

# ========= NOVOS COMPONENTES DE EDIÇÃO =========
class EditarRegistroSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id); self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        farms = user_data.get("farms", [])
        options = []
        for idx, farm in enumerate(farms):
            farm_id = farm.get("farm_id", idx+1)
            produtos_desc = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in farm["produtos"])
            label = f"Farm #{farm_id} - {produtos_desc}"
            description = f"Data: {farm['data']}"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        if not options: options.append(discord.SelectOption(label="Nenhum registro encontrado", value="none", default=True))
        super().__init__(placeholder="Selecione o registro de farm...", min_values=1, max_values=1, options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.values[0] == "none": await interaction.followup.send("Nenhum registro de farm para editar.", ephemeral=True); return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data["farms"]):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True); return
        farm = user_data["farms"][idx]
        modal = EditarFarmModal(self.user_id, self.user_name, interaction.channel, idx, farm)
        await interaction.response.send_modal(modal)

class EditarFarmModal(Modal, title="Editar Registro de Farm"):
    chumbo = TextInput(label="CHUMBO - Nova quantidade", placeholder="0", required=False)
    capsula = TextInput(label="CÁPSULA - Nova quantidade", placeholder="0", required=False)
    polvora = TextInput(label="PÓLVORA - Nova quantidade", placeholder="0", required=False)
    def __init__(self, user_id, user_name, canal, farm_index, farm_atual):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
        self.farm_index = farm_index; self.farm_atual = farm_atual
        produtos_atuais = {p["produto"]: p["quantidade"] for p in farm_atual["produtos"]}
        self.chumbo.default = str(produtos_atuais.get("CHUMBO", ""))
        self.capsula.default = str(produtos_atuais.get("CAPSULA", ""))
        self.polvora.default = str(produtos_atuais.get("POLVORA", ""))
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        novos_produtos = []
        for campo, nome in [(self.chumbo,"CHUMBO"),(self.capsula,"CAPSULA"),(self.polvora,"POLVORA")]:
            if campo.value and campo.value.strip():
                try:
                    qtd = int(campo.value.strip())
                    if qtd > 0: novos_produtos.append({"produto":nome,"quantidade":qtd})
                except ValueError: pass
        if not novos_produtos: await interaction.followup.send("Nenhum produto válido. Edição cancelada.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a **nova print** comprovando a edição.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado. Edição cancelada.", ephemeral=True); return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.farm_index >= len(user_data["farms"]):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True); return
        antigo = user_data["farms"][self.farm_index]
        novo_registro = {"produtos":novos_produtos,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":nova_imagem_url,"validado":True,"farm_id":antigo.get("farm_id", self.farm_index+1)}
        user_data["farms"][self.farm_index] = novo_registro; salvar_dados()
        embed = discord.Embed(title="✏️ REGISTRO DE FARM EDITADO", description=f"**Usuário:** <@{self.user_id}>\n**Farm ID:** {novo_registro['farm_id']}", color=discord.Color.blue(), timestamp=datetime.now())
        produtos_str = "\n".join(f"🔫 **{p['produto']}:** {p['quantidade']} itens" for p in novos_produtos)
        embed.add_field(name="Novos valores", value=produtos_str, inline=False)
        embed.add_field(name="Data da edição", value=novo_registro["data"], inline=False)
        embed.set_image(url=nova_imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Registro #{novo_registro['farm_id']} editado com sucesso!", ephemeral=True)
        await log_acao("editar_farm", interaction.user, f"Usuário: {self.user_name}\nFarm ID: {novo_registro['farm_id']}\nNovos produtos: {produtos_str}", 0x3498db)
        await atualizar_ranking()

class EditarDinheiroSujoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id); self.user_name = user_name
        user_data = dados["usuarios"].get(self.user_id, {})
        transacoes = user_data.get("transacoes_dinheiro_sujo", [])
        options = []
        for idx, trans in enumerate(transacoes):
            valor = trans["valor"]; data = trans["data"]
            label = f"R$ {valor:,.2f} - {data}"[:100]
            description = f"Depósito de R$ {valor:,.2f}"[:100]
            options.append(discord.SelectOption(label=label, description=description, value=str(idx)))
        if not options: options.append(discord.SelectOption(label="Nenhum depósito encontrado", value="none", default=True))
        super().__init__(placeholder="Escolha o depósito de dinheiro sujo...", min_values=1, max_values=1, options=options[:25])
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if self.values[0] == "none": await interaction.followup.send("Nenhum depósito de dinheiro sujo para editar.", ephemeral=True); return
        idx = int(self.values[0])
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or idx >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True); return
        trans = user_data["transacoes_dinheiro_sujo"][idx]
        modal = EditarDinheiroSujoModal(self.user_id, self.user_name, interaction.channel, idx, trans)
        await interaction.response.send_modal(modal)

class EditarDinheiroSujoModal(Modal, title="Editar Depósito de Dinheiro Sujo"):
    novo_valor = TextInput(label="Novo valor (R$)", placeholder="Ex: 5000", required=True)
    def __init__(self, user_id, user_name, canal, trans_index, trans_atual):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
        self.trans_index = trans_index; self.trans_atual = trans_atual
        self.novo_valor.default = str(trans_atual["valor"])
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: novo_valor = float(self.novo_valor.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido.", ephemeral=True); return
        await interaction.followup.send("📸 Envie a **nova print** do comprovante.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado.", ephemeral=True); return
        nova_imagem_url = msg.attachments[0].url
        user_data = dados["usuarios"].get(self.user_id)
        if not user_data or self.trans_index >= len(user_data.get("transacoes_dinheiro_sujo", [])):
            await interaction.followup.send("Registro não encontrado.", ephemeral=True); return
        antiga = user_data["transacoes_dinheiro_sujo"][self.trans_index]
        nova_trans = {"valor": novo_valor,"data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url": nova_imagem_url,"registrado_por": interaction.user.id}
        user_data["transacoes_dinheiro_sujo"][self.trans_index] = nova_trans
        user_data["dinheiro_sujo"] = sum(t["valor"] for t in user_data["transacoes_dinheiro_sujo"])
        salvar_dados()
        embed = discord.Embed(title="✏️ DEPÓSITO DE DINHEIRO SUJO EDITADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor antigo:** R$ {antiga['valor']:,.2f}\n**Novo valor:** R$ {novo_valor:,.2f}", color=discord.Color.blue(), timestamp=datetime.now())
        embed.add_field(name="Data da edição", value=nova_trans["data"], inline=False)
        embed.set_image(url=nova_imagem_url); await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Depósito editado! Novo valor: R$ {novo_valor:,.2f}", ephemeral=True)
        await log_acao("editar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nNovo valor: R$ {novo_valor:,.2f}", 0x3498db)
        await atualizar_ranking()

class EscolherTipoEdicaoView(View):
    def __init__(self, user_id, user_name):
        super().__init__(timeout=120); self.user_id = user_id; self.user_name = user_name
        self.add_item(TipoEdicaoSelect(user_id, user_name))

class TipoEdicaoSelect(Select):
    def __init__(self, user_id, user_name):
        self.user_id = str(user_id); self.user_name = user_name
        options = [
            discord.SelectOption(label="📦 Produtos", description="Editar um registro de farm (CHUMBO/CÁPSULA/PÓLVORA)", value="produtos"),
            discord.SelectOption(label="💰 Dinheiro Sujo", description="Editar um depósito de dinheiro sujo", value="dinheiro_sujo")
        ]
        super().__init__(placeholder="O que você deseja editar?", min_values=1, max_values=1, options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        tipo = self.values[0]
        if tipo == "produtos":
            select = EditarRegistroSelect(self.user_id, self.user_name)
            view = View(timeout=None); view.add_item(select)
            await interaction.followup.send("Selecione o registro de farm que deseja editar:", view=view, ephemeral=True)
        else:
            select = EditarDinheiroSujoSelect(self.user_id, self.user_name)
            view = View(timeout=None); view.add_item(select)
            await interaction.followup.send("Selecione o depósito de dinheiro sujo que deseja editar:", view=view, ephemeral=True)

async def enviar_historico_farms(interaction, user_id, user_name):
    user_data = dados["usuarios"].get(str(user_id), {})
    farms = user_data.get("farms", [])
    transacoes = user_data.get("transacoes_dinheiro_sujo", [])
    if not farms and not transacoes:
        await interaction.followup.send("Você ainda não tem nenhum registro (farm de produtos ou dinheiro sujo).", ephemeral=True)
        return
    embed = discord.Embed(title=f"📋 Histórico de Registros - {user_name}", color=0x2ecc71)
    todos = []
    for farm in farms:
        todos.append({"tipo":"farm","data":farm["data"],"detalhes":farm})
    for trans in transacoes:
        todos.append({"tipo":"dinheiro_sujo","data":trans["data"],"detalhes":trans})
    todos.sort(key=lambda x: x["data"], reverse=True)
    ultimos = todos[:10]
    for registro in ultimos:
        tipo = registro["tipo"]; detalhes = registro["detalhes"]
        if tipo == "farm":
            farm_id = detalhes.get("farm_id","?")
            produtos_str = ", ".join(f"{p['produto']}: {p['quantidade']}" for p in detalhes["produtos"])
            print_url = detalhes.get("print_url","")
            valor = f"**Farm #{farm_id}** - {produtos_str}"
            if print_url: valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"📦 Farm #{farm_id} ({registro['data']})", value=valor, inline=False)
        else:
            valor_ds = detalhes["valor"]; print_url = detalhes.get("print_url","")
            valor = f"💰 R$ {valor_ds:,.2f}"
            if print_url: valor += f"\n🖼️ [Ver print]({print_url})"
            embed.add_field(name=f"💵 Dinheiro Sujo ({registro['data']})", value=valor, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=True)

class FarmChannelView(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None); self.user_id = user_id; self.user_name = user_name; self.canal_id = canal_id
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user): await interaction.response.send_message("Apenas o dono do canal!", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not (is_admin(interaction.user) or is_membro(interaction.user)): await interaction.response.send_message("Você não tem permissão para registrar dinheiro sujo.", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Editar Registro", style=discord.ButtonStyle.blurple, emoji="✏️", row=0)
    async def editar_registro(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user): await interaction.response.send_message("Apenas o dono do canal ou admin pode editar.", ephemeral=True); return
        view = EscolherTipoEdicaoView(self.user_id, self.user_name)
        await interaction.response.send_message("Escolha o tipo de registro que deseja editar:", view=view, ephemeral=True)
    @discord.ui.button(label="Fechar Caixa", style=discord.ButtonStyle.danger, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        user_data = dados["usuarios"].get(str(self.user_id),{}); total_sujo = user_data.get("dinheiro_sujo",0.0)
        if total_sujo <= 0: await interaction.followup.send("Nenhum dinheiro sujo acumulado.", ephemeral=True); return
        lavagem = total_sujo * 0.25; restante = total_sujo - lavagem; faccao = restante * 0.60; membro_base = restante * 0.40
        embed = discord.Embed(title="RESUMO DO FECHAMENTO", color=discord.Color.orange())
        embed.add_field(name="Total Farmado", value=f"R$ {total_sujo:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
        embed.add_field(name="Facção (60% do restante)", value=f"R$ {faccao:,.2f}", inline=True)
        embed.add_field(name="Membro Base (40%)", value=f"R$ {membro_base:,.2f}", inline=True)
        embed.set_footer(text="Clique no botão abaixo para continuar.")
        view = FechamentoSummaryView(self.user_id, self.user_name, interaction.channel, total_sujo, lavagem, faccao, membro_base)
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)
    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))
    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        fechamentos = dados["caixa_semana"].get(str(self.user_id),[])
        if not fechamentos: await interaction.followup.send("Nenhum fechamento.", ephemeral=True); return
        embed = discord.Embed(title="HISTÓRICO DE CAIXA", description=f"Últimos {min(10, len(fechamentos))} registros", color=discord.Color.blue())
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"],"%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            txt = f"Meta: {fech.get('meta_farm','?')}\n"
            if "produtos" in fech: txt += f"Chumbo: {fech['produtos']['chumbo']} | Cápsula: {fech['produtos']['capsula']} | Pólvora: {fech['produtos']['polvora']}\n"
            if "dinheiro_sujo" in fech:
                ds = fech["dinheiro_sujo"]; txt += f"Farm Sujo: R$ {ds['total']:,.2f}\nLavagem: R$ {ds['lavagem']:,.2f}\nFacção: R$ {ds['faccao']:,.2f}\nMembro Base: R$ {ds['membro_base']:,.2f}"
                if ds.get('bonus',0)>0: txt += f"\nBônus: R$ {ds['bonus']:,.2f}"; txt += f"\n**Pago: R$ {ds['pago']:,.2f}**"
            if fech.get('observacao'): txt += f"\n💌 {fech['observacao']}"
            embed.add_field(name=f"📅 {data}", value=txt, inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="Meus Registros", style=discord.ButtonStyle.primary, emoji="📋", row=2)
    async def meus_registros(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        await enviar_historico_farms(interaction, self.user_id, self.user_name)
    @discord.ui.button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?**", view=confirm_view, ephemeral=True)
    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)

class ConfirmResetSemanalView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=60); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    @discord.ui.button(label="Sim, resetar semana", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)]["farms"] = []
            dados["usuarios"][str(self.user_id)]["pagamentos"] = []
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0.0
            dados["usuarios"][str(self.user_id)]["transacoes_dinheiro_sujo"] = []
            salvar_dados()
        await interaction.followup.send("✅ Semana resetada com sucesso!", ephemeral=True)
        await log_admin("RESET SEMANAL", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}", 0xffa500); await atualizar_ranking()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button): await interaction.response.send_message("Reset cancelado.", ephemeral=True)

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60); self.user_id = user_id; self.canal = canal
    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        if str(self.user_id) in dados["canais"]: del dados["canais"][str(self.user_id)]; salvar_dados()
        await self.canal.delete(); await interaction.followup.send("Canal fechado!", ephemeral=True)
        await log_acao("fechar_canal", interaction.user, f"Canal {self.canal.name} fechado", 0xff0000)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button): await interaction.response.send_message("Cancelado!", ephemeral=True)

# ========= MODAIS ADMIN =========
class RemoverUsuarioModal(Modal, title="Remover Usuário"):
    user_id = TextInput(label="ID do usuário", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(self.user_id.value.strip()); user = await interaction.client.fetch_user(uid)
            if str(uid) in dados["usuarios_banidos"]: await interaction.followup.send("Usuário já removido!", ephemeral=True); return
            total = await limpar_logs_usuario(uid, user.name)
            await interaction.followup.send(f"✅ {user.mention} removido! Limpas: {total}", ephemeral=True)
            await log_admin("USUÁRIO REMOVIDO", f"{user.mention} por {interaction.user.mention}", 0xff0000); await atualizar_ranking()
        except Exception as e: await interaction.followup.send(f"Erro: {e}", ephemeral=True)

class BackupView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Criar Backup", style=discord.ButtonStyle.success, emoji="💾")
    async def criar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backup_nome = await salvar_backup_completo(interaction.user.name)
        await interaction.followup.send(f"✅ Backup **{backup_nome}** criado e salvo no canal de backups!", ephemeral=True)
        await log_admin("BACKUP CRIADO", f"Admin: {interaction.user.mention}\nArquivo: {backup_nome}", 0x00ff00)
    @discord.ui.button(label="Apagar Backups Locais", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def apagar_backups(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = [a for a in os.listdir('.') if a.startswith('backup_') and a.endswith('.json')]
        if not backups: await interaction.followup.send("Nenhum backup local encontrado.", ephemeral=True); return
        for b in backups: os.remove(b)
        await interaction.followup.send(f"{len(backups)} backup(s) locais deletados!", ephemeral=True)
        await log_admin("BACKUPS DELETADOS", f"Admin: {interaction.user.mention}\nQtd: {len(backups)}", 0xff0000)
    @discord.ui.button(label="Recarregar Backup", style=discord.ButtonStyle.primary, emoji="🔄")
    async def recarregar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = sorted(glob.glob("backup_completo_*.json"), reverse=True)
        if not backups: await interaction.followup.send("Nenhum backup encontrado para recarregar.", ephemeral=True); return
        view = RecarregarBackupSelectView(backups)
        await interaction.followup.send("Selecione o backup que deseja restaurar:", view=view, ephemeral=True)

class RecarregarBackupSelectView(View):
    def __init__(self, backups):
        super().__init__(timeout=120); self.backups = backups
        options = []
        for b in backups[:25]:
            try:
                with open(b,"r",encoding="utf-8") as f: data = json.load(f)
                info = f"{data.get('data_backup','?')} - {data.get('admin','?')}"
            except: info = b
            options.append(discord.SelectOption(label=info[:100], value=b))
        if options: self.add_item(BackupSelectDropdown(options))

class BackupSelectDropdown(Select):
    def __init__(self, options): super().__init__(placeholder="Escolha um backup para restaurar...", options=options)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        arquivo = self.values[0]
        try:
            with open(arquivo,"r",encoding="utf-8") as f: backup_data = json.load(f)
            if "dados" in backup_data: dados.clear(); dados.update(backup_data["dados"]); salvar_dados()
            await interaction.followup.send(f"✅ Backup restaurado com sucesso!\n**Arquivo:** {arquivo}\n**Data:** {backup_data.get('data_backup','?')}", ephemeral=True)
            await log_admin("BACKUP RESTAURADO", f"Admin: {interaction.user.mention}\nArquivo: {arquivo}", 0x00ff00); await atualizar_ranking()
        except Exception as e: await interaction.followup.send(f"Erro ao recarregar backup: {e}", ephemeral=True)

# ========= BOTÃO CRIAR CANAL =========
class BotaoCriarCanalView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if interaction.guild is None: await interaction.followup.send("Use em um servidor!", ephemeral=True); return
        if not interaction.guild.me.guild_permissions.manage_channels: await interaction.followup.send("Bot precisa de permissão de Administrador.", ephemeral=True); return
        if str(interaction.user.id) in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][str(interaction.user.id)])
            if canal: await interaction.followup.send(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True); return
            else: del dados["canais"][str(interaction.user.id)]; salvar_dados()
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria: await interaction.followup.send("Categoria não encontrada!", ephemeral=True); return
            overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False), interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, add_reactions=True, read_message_history=True), interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, attach_files=True, embed_links=True, read_message_history=True)}
            cargo_admin = interaction.guild.get_role(CARGO_ADMIN_GERAL_ID)
            if cargo_admin: overwrites[cargo_admin] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, manage_channels=True)
            nome = f"farm-{interaction.user.name}".lower().replace(" ","-")[:90]
            canal = await categoria.create_text_channel(nome, overwrites=overwrites)
            dados["canais"][str(interaction.user.id)] = canal.id; salvar_dados()
            view = FarmChannelView(interaction.user.id, interaction.user.name, canal.id)
            tipo = "ADMIN" if is_admin(interaction.user) else "MEMBRO"
            embed = discord.Embed(title="SEU CANAL PRIVADO", description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES DISPONÍVEIS PARA {tipo}:**\n📦 **Farm Produtos** - Registrar farm de produtos (com print)\n💰 **Farm Dinheiro Sujo** - Registrar dinheiro sujo (com print)\n✏️ **Editar Registro** - Corrigir um registro\n📋 **Meus Registros** - Ver histórico completo", color=discord.Color.green())
            if tipo == "ADMIN": embed.description += "\n\n**BOTÕES ADMINISTRATIVOS:**\n📊 **Fechar Caixa** - Fechar caixa semanal\n✏️ **Mudar Nome** - Renomear canal\n📜 **Histórico Caixa** - Ver fechamentos\n🔄 **Reset Semanal** - Limpar dados da semana\n🗑️ **Fechar Canal** - Deletar canal"
            await canal.send(embed=embed, view=view)
            await log_acao("criar_canal", interaction.user, f"Canal criado: {canal.mention}", 0x00ff00)
            await interaction.followup.send(f"✅ Canal criado! Acesse: {canal.mention}", ephemeral=True); await atualizar_ranking()
        except Exception as e: await interaction.followup.send(f"Erro: {str(e)[:200]}", ephemeral=True)

# (Restante do código de lives, ações, eventos permanece igual ao que você já tinha)

# ========= SISTEMA DE LIVES =========
# ... (mantenha exatamente igual ao seu código original, sem alterações)

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    # (seu código original)
    pass

@bot.event
async def on_ready():
    # (seu código original)
    pass

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)
