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

# ========= CONFIGURAÇÕES =========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERRO: Token do Discord não encontrado!")
    sys.exit(1)

CARGO_ADMIN_ID = int(os.getenv("CARGO_ADMIN_ID", "1498104494226014319"))
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
        "last_notified": {}
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
        dados["usuarios"][str(user_id)] = {"farms":[],"pagamentos":[],"dinheiro_sujo":0,"nome":f"[REMOVIDO - {user_name}]","removido_em":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"removido_por":"sistema"}
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
    cores = {"criar_canal":0x00ff00,"registrar_farm":0x00ff00,"registrar_dinheiro_sujo":0xff0000,"pagar":0xffa500,"fechar_canal":0xff0000,"fechar_caixa":0xffa500,"reset_rank":0xff0000,"info":0x3498db,"admin":0x9b59b6,"setar_admin":0x9b59b6,"compra_venda":0x00ff00,"usuario_removido":0xff0000}
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

def is_admin(member) -> bool:
    if not hasattr(member, 'guild'): return False
    if member.guild.get_role(CARGO_ADMIN_ID) in member.roles: return True
    if str(member.id) in dados["admins"]: return True
    if member.guild_permissions.administrator: return True
    return False

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
            tot_pag = sum(p["valor"] for p in data["pagamentos"])
            qtd_pag = len(data["pagamentos"])
            din_sujo = data.get("dinheiro_sujo",0)
            usuarios_data.append({"nome":user.name,"user_id":uid,"total_chumbo":tot_chumbo,"total_capsula":tot_capsula,"total_polvora":tot_polvora,"total_pagamentos":tot_pag,"quantidade_pagamentos":qtd_pag,"dinheiro_sujo":din_sujo})
        except: continue
    emb = discord.Embed(title="RANKING GERAL", description=f"Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", color=discord.Color.gold())
    for nome, key in [("CHUMBO","total_chumbo"),("CAPSULA","total_capsula"),("POLVORA","total_polvora")]:
        lista = sorted(usuarios_data, key=lambda x: x[key], reverse=True)[:5]
        txt = ""
        for i,u in enumerate(lista,1):
            medalha = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}°"
            if u[key]>0: txt += f"{medalha} **{u['nome']}** - {u[key]:,} itens\n"
        emb.add_field(name=nome, value=txt or "Nenhum dado ainda", inline=False)
    lista_salario = sorted(usuarios_data, key=lambda x: x["total_pagamentos"], reverse=True)[:5]
    txt = ""
    for i,u in enumerate(lista_salario,1):
        medalha = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}°"
        if u["total_pagamentos"]>0: txt += f"{medalha} **{u['nome']}** - R$ {u['total_pagamentos']:,.2f} ({u['quantidade_pagamentos']} pagamentos)\n"
    emb.add_field(name="TOP SALÁRIO", value=txt or "Nenhum dado ainda", inline=False)
    lista_sujo = sorted(usuarios_data, key=lambda x: x["dinheiro_sujo"], reverse=True)[:5]
    txt = ""
    for i,u in enumerate(lista_sujo,1):
        medalha = "🥇" if i==1 else "🥈" if i==2 else "🥉" if i==3 else f"{i}°"
        if u["dinheiro_sujo"]>0: txt += f"{medalha} **{u['nome']}** - R$ {u['dinheiro_sujo']:,.2f}\n"
    emb.add_field(name="DINHEIRO SUJO", value=txt or "Nenhum dado ainda", inline=False)
    await canal.send(embed=emb, view=RankingView())

class RankingView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Atualizar Ranking", style=discord.ButtonStyle.primary, emoji="🔄")
    async def atualizar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        await atualizar_ranking()
        await interaction.followup.send("Ranking atualizado!", ephemeral=True)
    @discord.ui.button(label="Resetar Ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def resetar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_message("⚠️ ATENÇÃO! ...", view=ConfirmarResetView(), ephemeral=True)

class ConfirmarResetView(View):
    def __init__(self): super().__init__(timeout=60)
    @discord.ui.button(label="Sim, resetar ranking", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True, thinking=True)
        backup_nome = f"backup_rank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(backup_nome,"w",encoding="utf-8") as f: json.dump({"usuarios":dados["usuarios"].copy(),"data_backup":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.name}, f)
        await criar_canal_backup("novo", backup_nome)
        dados["usuarios"] = {}; dados["caixa_semana"] = {}; dados["dinheiro_sujo"] = {}
        salvar_dados()
        await log_acao("reset_rank", interaction.user, f"Ranking resetado por {interaction.user.mention}", 0xff0000)
        await log_admin("RANKING RESETADO", f"Admin: {interaction.user.mention}\nData: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0xff0000)
        await interaction.followup.send("Ranking resetado com sucesso!", ephemeral=True)
        await atualizar_ranking()
        self.stop()
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)
        self.stop()

class DinheiroSujoModal(Modal, title="Registrar Dinheiro Sujo"):
    quantidade = TextInput(label="Valor (R$)", placeholder="Ex: 5000", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: valor = float(self.quantidade.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0}
        if "dinheiro_sujo" not in dados["usuarios"][str(self.user_id)]: dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0
        dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] += valor
        salvar_dados()
        embed = discord.Embed(title="💰 DINHEIRO SUJO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}", color=discord.Color.red(), timestamp=datetime.now())
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"R$ {valor:,.2f} registrado como dinheiro sujo para {self.user_name}!", ephemeral=True)
        await log_acao("registrar_dinheiro_sujo", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xff0000)
        await atualizar_ranking()

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
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0}
        old_chumbo = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        old_capsula = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        old_polvora = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        registro = {"produtos":produtos,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url,"validado":True,"farm_id":len(dados["usuarios"][str(self.user_id)]["farms"])+1}
        dados["usuarios"][str(self.user_id)]["farms"].append(registro)
        salvar_dados()
        new_chumbo = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        new_capsula = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        new_polvora = sum(p["quantidade"] for f in dados["usuarios"][str(self.user_id)]["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        canal_user = bot.get_channel(dados["canais"].get(str(self.user_id)))
        if canal_user:
            for nome, old, new in [("CHUMBO",old_chumbo,new_chumbo), ("CAPSULA",old_capsula,new_capsula), ("POLVORA",old_polvora,new_polvora)]:
                if new // 600 > old // 600:
                    excedente = new % 600
                    await canal_user.send(f"🎉 **Parabéns! Você bateu a meta de 600 {nome}!**\nTotal acumulado: {new}\nVocê já tem {excedente} para a próxima meta de 600. Continue assim!")
        embed = discord.Embed(title="FARM PRODUTOS REGISTRADA COM SUCESSO", description=f"**Usuário:** <@{self.user_id}>\n", color=discord.Color.green())
        desc = "".join(f"🔫 **{p['produto']}:** {p['quantidade']} itens\n" for p in produtos)
        embed.description += desc
        embed.add_field(name="Data", value=datetime.now().strftime("%d/%m/%Y às %H:%M"), inline=False)
        embed.add_field(name="Total de farms", value=f"{len(dados['usuarios'][str(self.user_id)]['farms'])} farms", inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(embed=embed, ephemeral=True)
        produtos_str = ', '.join(f"{p['produto']}: {p['quantidade']}" for p in produtos)
        await log_acao("registrar_farm", interaction.user, f"Produtos: {produtos_str}")
        await log_admin("NOVA FARM PRODUTOS", f"Usuário: {interaction.user.mention}\nProdutos: {produtos_str}", 0x00ff00)
        await atualizar_ranking()

class PagamentoFarmModal(Modal, title="Registrar Pagamento"):
    valor = TextInput(label="Valor do Pagamento (R$)", placeholder="Ex: 500", required=True)
    def __init__(self, user_id, user_name, canal):
        super().__init__(); self.user_id = user_id; self.user_name = user_name; self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: valor = float(self.valor.value.replace(",","."))
        except ValueError: await interaction.followup.send("Valor inválido!", ephemeral=True); return
        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0}
        dados["usuarios"][str(self.user_id)]["pagamentos"].append({"valor":valor,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.id,"admin_nome":interaction.user.name,"tipo":"Pagamento","print_url":imagem_url})
        salvar_dados()
        try: await (await interaction.client.fetch_user(int(self.user_id))).send(embed=discord.Embed(title="PAGAMENTO RECEBIDO", description=f"Você recebeu R$ {valor:,.2f}!", color=discord.Color.green()).set_image(url=imagem_url))
        except: pass
        embed = discord.Embed(title="PAGAMENTO REGISTRADO", description=f"**Usuário:** <@{self.user_id}>\n**Valor:** R$ {valor:,.2f}\n**Admin:** {interaction.user.mention}", color=discord.Color.green(), timestamp=datetime.now()).set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {valor:,.2f} registrado!", ephemeral=True)
        await log_acao("pagar", interaction.user, f"Usuário: {self.user_name}\nValor: R$ {valor:,.2f}", 0xffa500)
        await atualizar_ranking()

class FechamentoSummaryView(View):
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__(timeout=300)
        self.user_id = user_id; self.user_name = user_name; self.canal = canal
        self.total_sujo = total_sujo; self.lavagem = lavagem; self.faccao = faccao; self.membro_base = membro_base
    @discord.ui.button(label="Continuar Fechamento", style=discord.ButtonStyle.success, emoji="✅")
    async def continuar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(FechamentoCaixaModal(self.user_id, self.user_name, self.canal, self.total_sujo, self.lavagem, self.faccao, self.membro_base))

class FechamentoCaixaModal(Modal, title="Finalizar Fechamento"):
    meta_farm = TextInput(label="Meta de Farm (Sim/Não)", placeholder="Digite Sim ou Não", required=True)
    bonus = TextInput(label="Bônus (R$) - Opcional", placeholder="Ex: 500 (deixe 0 se não houver)", required=False, default="0")
    observacao = TextInput(label="Observação (mensagem carinhosa)", placeholder="Deixe uma mensagem para o usuário...", required=False, style=discord.TextStyle.long)
    def __init__(self, user_id, user_name, canal, total_sujo, lavagem, faccao, membro_base):
        super().__init__()
        self.user_id = user_id; self.user_name = user_name; self.canal = canal
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
        if str(self.user_id) not in dados["usuarios"]: dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0}
        user_data = dados["usuarios"][str(self.user_id)]
        if pagamento_final > 0:
            user_data["pagamentos"].append({
                "valor": pagamento_final,
                "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin": interaction.user.id,
                "admin_nome": interaction.user.name,
                "tipo": "Fechamento de Caixa Semanal",
                "detalhes": {"total_sujo":self.total_sujo,"lavagem":self.lavagem,"faccao":self.faccao,"membro_base":self.membro_base,"bonus":bonus_valor},
                "print_url": imagem_url
            })
        tot_chumbo = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="CHUMBO")
        tot_capsula = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="CAPSULA")
        tot_polvora = sum(p["quantidade"] for f in user_data["farms"] for p in f["produtos"] if p["produto"]=="POLVORA")
        fechamento = {
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.name,
            "admin_id": interaction.user.id,
            "usuario": self.user_name,
            "usuario_id": self.user_id,
            "meta_farm": meta,
            "produtos": {"chumbo":tot_chumbo, "capsula":tot_capsula, "polvora":tot_polvora},
            "dinheiro_sujo": {"total": self.total_sujo, "lavagem": self.lavagem, "faccao": self.faccao, "membro_base": self.membro_base, "bonus": bonus_valor, "pago": pagamento_final},
            "print_url": imagem_url,
            "observacao": obs
        }
        if str(self.user_id) not in dados["caixa_semana"]: dados["caixa_semana"][str(self.user_id)] = []
        dados["caixa_semana"][str(self.user_id)].append(fechamento)
        salvar_dados()
        embed = discord.Embed(title="FECHAMENTO DE CAIXA SEMANAL", description=f"**{self.user_name}** fechou a semana!", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Meta de Farm", value=meta, inline=False)
        if tot_chumbo>0 or tot_capsula>0 or tot_polvora>0:
            embed.add_field(name="Produtos", value=f"🔫 Chumbo: {tot_chumbo}\n💣 Cápsula: {tot_capsula}\n💥 Pólvora: {tot_polvora}", inline=False)
        embed.add_field(name="Total Farmado", value=f"R$ {self.total_sujo:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {self.lavagem:,.2f}", inline=True)
        embed.add_field(name="Facção (60%)", value=f"R$ {self.faccao:,.2f}", inline=True)
        embed.add_field(name="Membro Base (40%)", value=f"R$ {self.membro_base:,.2f}", inline=True)
        if bonus_valor > 0: embed.add_field(name="Bônus", value=f"R$ {bonus_valor:,.2f}", inline=True)
        embed.add_field(name="💰 Pagamento Final", value=f"R$ {pagamento_final:,.2f}", inline=False)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        if obs: embed.add_field(name="💌 Mensagem", value=obs, inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)
        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)
        await interaction.followup.send(f"Pagamento de R$ {pagamento_final:,.2f} registrado!", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nPagamento: R$ {pagamento_final}", 0xffa500)
        await atualizar_ranking()

class VendaModal(Modal, title="Venda de Munição"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_compradora = TextInput(label="Facção Compradora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Venda", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value); valor = float(self.valor_total.value.replace(",","."))
        except: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await criar_canal_compra_venda_log("venda", {"Tipo":"VENDA","Quantidade":f"{qtd:,} munições","Valor Total":f"R$ {valor:,.2f}","Facção Compradora":self.faccao_compradora.value,"Responsável":self.responsavel.value,"Registrado por":interaction.user.mention})
        embed = discord.Embed(title="VENDA DE MUNIÇÃO", color=discord.Color.green())
        embed.add_field(name="Quantidade", value=f"{qtd:,}"); embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}")
        embed.add_field(name="Facção Compradora", value=self.faccao_compradora.value); embed.add_field(name="Responsável", value=self.responsavel.value)
        canal = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal: await canal.send(embed=embed); dados["compras_vendas"].append({"tipo":"venda","quantidade":qtd,"valor_total":valor,"faccao_compradora":self.faccao_compradora.value,"responsavel":self.responsavel.value,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}); salvar_dados(); await interaction.followup.send("Venda registrada!", ephemeral=True)
        else: await interaction.followup.send("Canal de vendas não encontrado!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Venda: {qtd} munições - R$ {valor}", 0x00ff00)

class CompraModal(Modal, title="Compra de Produto"):
    quantidade = TextInput(label="Quantidade", placeholder="Ex: 1000", required=True)
    produto = TextInput(label="Produto", placeholder="Ex: Munição", required=True)
    valor_total = TextInput(label="Valor Total (R$)", placeholder="Ex: 500", required=True)
    faccao_vendedora = TextInput(label="Facção Vendedora", placeholder="Ex: Primeiro Comando", required=True)
    responsavel = TextInput(label="Responsável pela Compra", placeholder="Ex: @usuario ou nome", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try: qtd = int(self.quantidade.value); valor = float(self.valor_total.value.replace(",","."))
        except: await interaction.followup.send("Valores inválidos!", ephemeral=True); return
        await criar_canal_compra_venda_log("compra", {"Tipo":"COMPRA","Quantidade":f"{qtd:,}","Produto":self.produto.value,"Valor Total":f"R$ {valor:,.2f}","Facção Vendedora":self.faccao_vendedora.value,"Responsável":self.responsavel.value,"Registrado por":interaction.user.mention})
        embed = discord.Embed(title="COMPRA DE PRODUTO", color=discord.Color.blue())
        embed.add_field(name="Quantidade", value=f"{qtd:,}"); embed.add_field(name="Produto", value=self.produto.value)
        embed.add_field(name="Valor Total", value=f"R$ {valor:,.2f}"); embed.add_field(name="Facção Vendedora", value=self.faccao_vendedora.value)
        embed.add_field(name="Responsável", value=self.responsavel.value)
        canal = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal: await canal.send(embed=embed); dados["compras_vendas"].append({"tipo":"compra","quantidade":qtd,"produto":self.produto.value,"valor_total":valor,"faccao_vendedora":self.faccao_vendedora.value,"responsavel":self.responsavel.value,"registrado_por":interaction.user.id,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S")}); salvar_dados(); await interaction.followup.send("Compra registrada!", ephemeral=True)
        else: await interaction.followup.send("Canal de vendas não encontrado!", ephemeral=True)
        await log_acao("compra_venda", interaction.user, f"Compra: {qtd} x {self.produto.value} - R$ {valor}", 0x00ff00)

class CompraVendaView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Venda de Munição", style=discord.ButtonStyle.success, emoji="💸")
    async def venda(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(VendaModal())
    @discord.ui.button(label="Compra de Produto", style=discord.ButtonStyle.primary, emoji="🛒")
    async def compra(self, interaction: discord.Interaction, button: Button): await interaction.response.send_modal(CompraModal())

class MudarNomeModal(Modal, title="Mudar Nome do Canal"):
    novo_nome = TextInput(label="Novo nome", placeholder="Ex: farm-lucas", required=True, max_length=90)
    def __init__(self, canal): super().__init__(); self.canal = canal
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        nome = ''.join(c for c in self.novo_nome.value.lower().replace(" ","-") if c.isalnum() or c=='-') or "farm"
        try: await self.canal.edit(name=nome); await interaction.response.send_message(f"Nome alterado para {nome}", ephemeral=True)
        except Exception as e: await interaction.response.send_message(f"Erro: {str(e)[:100]}", ephemeral=True)

class FarmChannelViewMembro(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None); self.user_id = user_id; self.user_name = user_name; self.canal_id = canal_id
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user): await interaction.response.send_message("Apenas o dono do canal!", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))

class FarmChannelViewAdmin(View):
    def __init__(self, user_id, user_name, canal_id):
        super().__init__(timeout=None); self.user_id = user_id; self.user_name = user_name; self.canal_id = canal_id
    @discord.ui.button(label="Farm Produtos", style=discord.ButtonStyle.success, emoji="📦", row=0)
    async def farm_produtos(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id and not is_admin(interaction.user): await interaction.response.send_message("Apenas o dono do canal!", ephemeral=True); return
        await interaction.response.send_modal(FarmProdutosModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Farm Dinheiro Sujo", style=discord.ButtonStyle.danger, emoji="💰", row=0)
    async def farm_dinheiro_sujo(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(DinheiroSujoModal(self.user_id, self.user_name, interaction.channel))
    @discord.ui.button(label="Fechar Caixa", style=discord.ButtonStyle.danger, emoji="📊", row=1)
    async def fechar_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        user_data = dados["usuarios"].get(str(self.user_id), {})
        total_sujo = user_data.get("dinheiro_sujo", 0.0)
        if total_sujo <= 0:
            await interaction.response.send_message("Nenhum dinheiro sujo acumulado.", ephemeral=True); return
        lavagem = total_sujo * 0.25
        restante = total_sujo - lavagem
        faccao = restante * 0.60
        membro_base = restante * 0.40
        embed = discord.Embed(title="RESUMO DO FECHAMENTO", color=discord.Color.orange())
        embed.add_field(name="Total Farmado", value=f"R$ {total_sujo:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
        embed.add_field(name="Facção (60% do restante)", value=f"R$ {faccao:,.2f}", inline=True)
        embed.add_field(name="Membro Base (40%)", value=f"R$ {membro_base:,.2f}", inline=True)
        embed.set_footer(text="Clique no botão abaixo para continuar.")
        view = FechamentoSummaryView(self.user_id, self.user_name, interaction.channel, total_sujo, lavagem, faccao, membro_base)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)
    @discord.ui.button(label="Mudar Nome", style=discord.ButtonStyle.secondary, emoji="✏️", row=1)
    async def mudar_nome(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_modal(MudarNomeModal(interaction.channel))
    @discord.ui.button(label="Histórico Caixa", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def historico_caixa(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        fechamentos = dados["caixa_semana"].get(str(self.user_id), [])
        if not fechamentos: await interaction.response.send_message("Nenhum fechamento.", ephemeral=True); return
        embed = discord.Embed(title="HISTÓRICO DE CAIXA", description=f"Últimos {min(10, len(fechamentos))} registros", color=discord.Color.blue())
        for fech in fechamentos[-10:]:
            data = datetime.strptime(fech["data"], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
            txt = f"Meta: {fech.get('meta_farm','?')}\n"
            if "produtos" in fech:
                txt += f"Chumbo: {fech['produtos']['chumbo']} | Cápsula: {fech['produtos']['capsula']} | Pólvora: {fech['produtos']['polvora']}\n"
            if "dinheiro_sujo" in fech:
                ds = fech["dinheiro_sujo"]
                txt += f"Farm Sujo: R$ {ds['total']:,.2f}\nLavagem: R$ {ds['lavagem']:,.2f}\nFacção: R$ {ds['faccao']:,.2f}\nMembro Base: R$ {ds['membro_base']:,.2f}"
                if ds.get('bonus',0)>0: txt += f"\nBônus: R$ {ds['bonus']:,.2f}"
                txt += f"\n**Pago: R$ {ds['pago']:,.2f}**"
            if fech.get('observacao'): txt += f"\n💌 {fech['observacao']}"
            embed.add_field(name=f"📅 {data}", value=txt, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    @discord.ui.button(label="Reset Semanal", style=discord.ButtonStyle.danger, emoji="🔄", row=2)
    async def reset_semanal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        confirm_view = ConfirmResetSemanalView(self.user_id, self.user_name, interaction.channel)
        await interaction.response.send_message("⚠️ **Tem certeza que deseja resetar a semana?** Todos os dados (farms, dinheiro sujo) serão zerados!", view=confirm_view, ephemeral=True)
    @discord.ui.button(label="Fechar Canal", style=discord.ButtonStyle.danger, emoji="🗑️", row=2)
    async def fechar_canal(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.send_message("⚠️ Tem certeza?", view=ConfirmarFechamentoView(self.user_id, interaction.channel), ephemeral=True)

class ConfirmResetSemanalView(View):
    def __init__(self, user_id, user_name, canal):
        super().__init__(timeout=60)
        self.user_id = user_id; self.user_name = user_name; self.canal = canal
    @discord.ui.button(label="Sim, resetar semana", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if str(self.user_id) in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)]["farms"] = []
            dados["usuarios"][str(self.user_id)]["pagamentos"] = []
            dados["usuarios"][str(self.user_id)]["dinheiro_sujo"] = 0.0
            salvar_dados()
            await interaction.response.send_message("✅ Semana resetada com sucesso!", ephemeral=True)
            await log_admin("RESET SEMANAL", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}", 0xffa500)
            await atualizar_ranking()
        else:
            await interaction.response.send_message("Usuário não encontrado.", ephemeral=True)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Reset cancelado.", ephemeral=True)

class ConfirmarFechamentoView(View):
    def __init__(self, user_id, canal):
        super().__init__(timeout=60); self.user_id = user_id; self.canal = canal
    @discord.ui.button(label="Sim, fechar", style=discord.ButtonStyle.danger, emoji="✅")
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        if str(self.user_id) in dados["canais"]: del dados["canais"][str(self.user_id)]; salvar_dados()
        await self.canal.delete()
        await interaction.response.send_message("Canal fechado!", ephemeral=True)
        await log_acao("fechar_canal", interaction.user, f"Canal {self.canal.name} fechado", 0xff0000)
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancelar(self, interaction: discord.Interaction, button: Button): await interaction.response.send_message("Cancelado!", ephemeral=True)

class RemoverUsuarioModal(Modal, title="Remover Usuário"):
    user_id = TextInput(label="ID do usuário", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            uid = int(self.user_id.value.strip())
            user = await interaction.client.fetch_user(uid)
            if str(uid) in dados["usuarios_banidos"]: await interaction.followup.send("Usuário já removido!", ephemeral=True); return
            total = await limpar_logs_usuario(uid, user.name)
            await interaction.followup.send(f"✅ {user.mention} removido! Limpas: {total}", ephemeral=True)
            await log_admin("USUÁRIO REMOVIDO", f"{user.mention} por {interaction.user.mention}", 0xff0000)
            await atualizar_ranking()
            if interaction.guild:
                member = interaction.guild.get_member(uid)
                if member and interaction.guild.get_role(CARGO_ADMIN_ID) in member.roles:
                    await member.remove_roles(interaction.guild.get_role(CARGO_ADMIN_ID))
        except Exception as e: await interaction.followup.send(f"Erro: {e}", ephemeral=True)

class BackupView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Criar Backup", style=discord.ButtonStyle.success, emoji="💾")
    async def criar_backup(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        nome = f"backup_completo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(nome,"w",encoding="utf-8") as f: json.dump({"data_backup":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"admin":interaction.user.name,"dados":dados.copy()}, f)
        await criar_canal_backup("novo", nome)
        await interaction.followup.send("Backup criado!", ephemeral=True)
        await log_admin("BACKUP CRIADO", f"Admin: {interaction.user.mention}", 0x00ff00)
    @discord.ui.button(label="Apagar Backups", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def apagar_backups(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user): await interaction.response.send_message("Sem permissão!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)
        backups = [a for a in os.listdir('.') if a.startswith('backup_') and a.endswith('.json')]
        if not backups: await interaction.followup.send("Nenhum backup.", ephemeral=True); return
        for b in backups: await criar_canal_backup("deletado", b); os.remove(b)
        await interaction.followup.send(f"{len(backups)} backups deletados!", ephemeral=True)
        await log_admin("BACKUPS DELETADOS", f"Admin: {interaction.user.mention}\nQtd: {len(backups)}", 0xff0000)

class BotaoCriarCanalView(View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="Criar Meu Canal Privado", style=discord.ButtonStyle.success, emoji="🔓")
    async def criar_canal(self, interaction: discord.Interaction, button: Button):
        if interaction.guild is None: await interaction.response.send_message("Use em um servidor!", ephemeral=True); return
        if not interaction.guild.me.guild_permissions.manage_channels: await interaction.response.send_message("Bot precisa de permissão de Administrador.", ephemeral=True); return
        if str(interaction.user.id) in dados["canais"]:
            canal = interaction.guild.get_channel(dados["canais"][str(interaction.user.id)])
            if canal: await interaction.response.send_message(f"Você já possui um canal! Acesse: {canal.mention}", ephemeral=True); return
            else: del dados["canais"][str(interaction.user.id)]; salvar_dados()
        await interaction.response.send_message("🔄 Criando seu canal...", ephemeral=True)
        try:
            categoria = interaction.guild.get_channel(CATEGORIA_FARMS_ID)
            if not categoria: await interaction.edit_original_response(content="Categoria não encontrada!"); return
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, add_reactions=True, read_message_history=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, attach_files=True, embed_links=True, read_message_history=True)
            }
            cargo = interaction.guild.get_role(CARGO_ADMIN_ID)
            if cargo: overwrites[cargo] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True, manage_channels=True)
            nome = f"farm-{interaction.user.name}".lower().replace(" ","-")[:90]
            canal = await categoria.create_text_channel(nome, overwrites=overwrites)
            dados["canais"][str(interaction.user.id)] = canal.id; salvar_dados()
            if is_admin(interaction.user):
                view = FarmChannelViewAdmin(interaction.user.id, interaction.user.name, canal.id)
                tipo = "ADMIN"
            else:
                view = FarmChannelViewMembro(interaction.user.id, interaction.user.name, canal.id)
                tipo = "MEMBRO"
            embed = discord.Embed(title="SEU CANAL PRIVADO", description=f"Bem-vindo(a) {interaction.user.mention}!\n\n🔒 Apenas você e administradores têm acesso.\n\n**BOTÕES DISPONÍVEIS PARA {tipo}:**\n📦 **Farm Produtos** - Registrar farm de produtos (com print)\n💰 **Farm Dinheiro Sujo** - Registrar dinheiro sujo (com print)", color=discord.Color.green())
            if tipo == "ADMIN":
                embed.description += "\n\n**BOTÕES ADMINISTRATIVOS:**\n📊 **Fechar Caixa** - Fechar caixa semanal\n✏️ **Mudar Nome** - Renomear canal\n📜 **Histórico Caixa** - Ver fechamentos\n🔄 **Reset Semanal** - Limpar dados da semana\n🗑️ **Fechar Canal** - Deletar canal"
            await canal.send(embed=embed, view=view)
            await log_acao("criar_canal", interaction.user, f"Canal criado: {canal.mention}", 0x00ff00)
            await interaction.edit_original_response(content=f"✅ Canal criado! Acesse: {canal.mention}")
            await atualizar_ranking()
        except Exception as e: await interaction.edit_original_response(content=f"Erro: {str(e)[:200]}")

# ========= SISTEMA DE LIVES (com correções de nome e observação) =========
def extract_platform_from_url(url: str):
    url = url.strip().lower()
    if "twitch.tv" in url:
        match = re.search(r"twitch\.tv/([a-zA-Z0-9_]+)", url)
        if match: return ("twitch", match.group(1))
    elif "youtube.com" in url or "youtu.be" in url:
        if "youtube.com/@" in url:
            return ("youtube", url.split("@")[-1].split("/")[0])
        elif "youtube.com/channel/" in url:
            return ("youtube", url.split("/channel/")[-1].split("?")[0])
        elif "youtube.com/c/" in url:
            return ("youtube", url.split("/c/")[-1].split("/")[0])
    elif "kick.com" in url:
        match = re.search(r"kick\.com/([a-zA-Z0-9_]+)", url)
        if match: return ("kick", match.group(1))
    elif "tiktok.com" in url:
        match = re.search(r"tiktok\.com/@([a-zA-Z0-9_.]+)", url)
        if match: return ("tiktok", match.group(1))
    return (None, None)

twitch_token = None
twitch_token_expiry = 0

async def get_twitch_token():
    global twitch_token, twitch_token_expiry
    if twitch_token and datetime.utcnow().timestamp() < twitch_token_expiry:
        return twitch_token
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET:
        return None
    async with aiohttp.ClientSession() as session:
        async with session.post("https://id.twitch.tv/oauth2/token", params={
            "client_id": TWITCH_CLIENT_ID,
            "client_secret": TWITCH_CLIENT_SECRET,
            "grant_type": "client_credentials"
        }) as resp:
            if resp.status == 200:
                data = await resp.json()
                twitch_token = data["access_token"]
                twitch_token_expiry = datetime.utcnow().timestamp() + data["expires_in"] - 60
                return twitch_token
    return None

async def check_twitch_lives(streamers):
    token = await get_twitch_token()
    if not token: return {}
    usernames = [s for s in streamers if s]
    if not usernames: return {}
    headers = {"Client-ID": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"}
    url = "https://api.twitch.tv/helix/streams?user_login=" + "&user_login=".join(usernames)
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {s["user_login"].lower(): s for s in data.get("data", [])}
    return {}

async def check_youtube_lives(streamers):
    if not YOUTUBE_API_KEY: return {}
    live_data = {}
    for ch_id in streamers:
        if not ch_id: continue
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={ch_id}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for item in data.get("items", []):
                        live_data[ch_id] = item
    return live_data

@tasks.loop(minutes=1)
async def live_check_loop():
    for server_id_str in dados["lives"]["config"]:
        config = dados["lives"]["config"][server_id_str]
        guild = bot.get_guild(int(server_id_str))
        if not guild: continue
        plataformas = config.get("platforms", {"twitch":True,"youtube":True,"kick":True,"tiktok":True})
        canal_id = config.get("channel")
        canal = bot.get_channel(canal_id) if canal_id else None
        role_id = config.get("role")
        role_mention = f"<@&{role_id}>" if role_id else ""
        streamers_dict = dados["lives"]["streamers"].get(server_id_str, {})
        if plataformas.get("twitch"):
            twitch_users = [data.get("twitch") for data in streamers_dict.values() if data.get("twitch")]
            lives = await check_twitch_lives(twitch_users)
            for uid, data in streamers_dict.items():
                twitch_name = data.get("twitch")
                if twitch_name and twitch_name.lower() in lives:
                    last_key = f"twitch_{uid}"
                    live_info = lives[twitch_name.lower()]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != live_info["id"]:
                        dados["lives"]["last_notified"][last_key] = live_info["id"]
                        nome_streamer = data.get("nome", twitch_name)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao: desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NA TWITCH", description=desc, color=0x9146ff)
                            embed.add_field(name="Título", value=live_info['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://twitch.tv/{twitch_name}", inline=False)
                            await canal.send(content=role_mention, embed=embed)
        if plataformas.get("youtube"):
            yt_users = [data.get("youtube") for data in streamers_dict.values() if data.get("youtube")]
            lives = await check_youtube_lives(yt_users)
            for uid, data in streamers_dict.items():
                yt_ch = data.get("youtube")
                if yt_ch and yt_ch in lives:
                    last_key = f"yt_{uid}"
                    video = lives[yt_ch]
                    video_id = video["id"]["videoId"]
                    last = dados["lives"]["last_notified"].get(last_key)
                    if last != video_id:
                        dados["lives"]["last_notified"][last_key] = video_id
                        nome_streamer = data.get("nome", yt_ch)
                        observacao = data.get("observacao", "")
                        if canal:
                            desc = f"**{nome_streamer}** está ao vivo!"
                            if observacao: desc += f"\n{observacao}"
                            embed = discord.Embed(title="🔴 LIVE NO YOUTUBE", description=desc, color=0xff0000)
                            embed.add_field(name="Título", value=video['snippet']['title'], inline=False)
                            embed.add_field(name="Link", value=f"https://youtube.com/watch?v={video_id}", inline=False)
                            await canal.send(content=role_mention, embed=embed)
    salvar_dados()

@live_check_loop.before_loop
async def before_live_check():
    await bot.wait_until_ready()

class LiveConfigView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    async def get_config(self):
        return dados["lives"]["config"].setdefault(str(self.server_id), {
            "channel": None,
            "role": None,
            "platforms": {"twitch": True, "youtube": True, "kick": True, "tiktok": True}
        })

    async def build_embed(self):
        config = await self.get_config()
        canal_info = f"<#{config['channel']}>" if config['channel'] else "Não definido"
        cargo_info = f"<@&{config['role']}>" if config['role'] else "Não definido"
        plats = config['platforms']
        embed = discord.Embed(title="🔔 NOTIFICAÇÃO DE LIVES", color=0x9b59b6)
        embed.add_field(name="Canal", value=canal_info, inline=False)
        embed.add_field(name="Cargo (ping)", value=cargo_info, inline=False)
        status = "\n".join([
            f"Twitch: {'✅ Ativado' if plats['twitch'] else '❌ Desativado'}",
            f"YouTube: {'✅ Ativado' if plats['youtube'] else '❌ Desativado'}",
            f"Kick: {'✅ Ativado' if plats['kick'] else '❌ Desativado'}",
            f"TikTok: {'✅ Ativado' if plats['tiktok'] else '❌ Desativado'}"
        ])
        embed.add_field(name="Plataformas Monitoradas", value=status, inline=False)
        return embed

    @discord.ui.button(label="Definir Canal", style=discord.ButtonStyle.primary, emoji="📝")
    async def set_channel(self, interaction: discord.Interaction, button: Button):
        modal = SetCanalModal(self.server_id, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Configuração", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def configuracao(self, interaction: discord.Interaction, button: Button):
        view = ConfigSteamersView(self.server_id, self)
        embed = discord.Embed(title="⚙️ CONFIGURAÇÃO DE STREAMERS", description="Gerencie os streamers e plataformas.", color=0x7289da)
        await interaction.response.edit_message(embed=embed, view=view)

class SetCanalModal(Modal, title="Definir Canal e Cargo"):
    canal_id = TextInput(label="ID do canal de notícias", placeholder="Ex: 123456789012345678", required=True)
    cargo_id = TextInput(label="ID do cargo para mencionar", placeholder="Ex: 987654321098765432", required=True)
    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view
    async def on_submit(self, interaction: discord.Interaction):
        try:
            cid = int(self.canal_id.value.strip())
            rid = int(self.cargo_id.value.strip())
            config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms":{"twitch":True,"youtube":True,"kick":True,"tiktok":True}})
            config["channel"] = cid
            config["role"] = rid
            salvar_dados()
            embed = await self.parent_view.build_embed()
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
        except:
            await interaction.response.send_message("IDs inválidos.", ephemeral=True)

class ConfigSteamersView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=None)
        self.server_id = server_id
        self.parent_view = parent_view

    @discord.ui.button(label="Adicionar Streamer", style=discord.ButtonStyle.success, emoji="➕")
    async def add(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddStreamerByLinkModal(self.server_id, self.parent_view))

    @discord.ui.button(label="Remover Streamer", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def remove(self, interaction: discord.Interaction, button: Button):
        streamers = dados["lives"]["streamers"].get(str(self.server_id), {})
        if not streamers:
            await interaction.response.send_message("Nenhum streamer cadastrado para remover.", ephemeral=True); return
        view = RemoveStreamerSelectView(self.server_id, self.parent_view)
        await interaction.response.send_message("Selecione o streamer que deseja remover:", view=view, ephemeral=True)

    @discord.ui.button(label="Twitch", style=discord.ButtonStyle.primary, emoji="📺", row=1)
    async def toggle_twitch(self, interaction: discord.Interaction, button: Button):
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms":{"twitch":True}})
        config["platforms"]["twitch"] = not config["platforms"].get("twitch", True)
        salvar_dados()
        await interaction.response.defer()

    @discord.ui.button(label="YouTube", style=discord.ButtonStyle.danger, emoji="▶️", row=1)
    async def toggle_youtube(self, interaction: discord.Interaction, button: Button):
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms":{"youtube":True}})
        config["platforms"]["youtube"] = not config["platforms"].get("youtube", True)
        salvar_dados()
        await interaction.response.defer()

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.success, emoji="🟢", row=1)
    async def toggle_kick(self, interaction: discord.Interaction, button: Button):
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms":{"kick":True}})
        config["platforms"]["kick"] = not config["platforms"].get("kick", True)
        salvar_dados()
        await interaction.response.defer()

    @discord.ui.button(label="TikTok", style=discord.ButtonStyle.secondary, emoji="🎵", row=1)
    async def toggle_tiktok(self, interaction: discord.Interaction, button: Button):
        config = dados["lives"]["config"].setdefault(str(self.server_id), {"platforms":{"tiktok":True}})
        config["platforms"]["tiktok"] = not config["platforms"].get("tiktok", True)
        salvar_dados()
        await interaction.response.defer()

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.secondary, emoji="↩️", row=2)
    async def voltar(self, interaction: discord.Interaction, button: Button):
        embed = await self.parent_view.build_embed()
        await interaction.response.edit_message(embed=embed, view=self.parent_view)

class RemoveStreamerSelectView(View):
    def __init__(self, server_id, parent_view):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.parent_view = parent_view
        streamers = dados["lives"]["streamers"].get(str(server_id), {})
        options = []
        for uid, data in streamers.items():
            nome = data.get("nome", uid)
            plats = []
            if data.get("twitch"): plats.append("Twitch")
            if data.get("youtube"): plats.append("YouTube")
            if data.get("kick"): plats.append("Kick")
            if data.get("tiktok"): plats.append("TikTok")
            desc = f"{nome} ({', '.join(plats)})" if plats else nome
            options.append(discord.SelectOption(label=desc[:100], value=uid))
        if options:
            self.add_item(StreamerRemoveDropdown(options, server_id, parent_view))

class StreamerRemoveDropdown(Select):
    def __init__(self, options, server_id, parent_view):
        super().__init__(placeholder="Escolha um streamer para remover...", options=options)
        self.server_id = server_id
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        uid = self.values[0]
        if str(self.server_id) in dados["lives"]["streamers"] and uid in dados["lives"]["streamers"][str(self.server_id)]:
            nome = dados["lives"]["streamers"][str(self.server_id)][uid].get("nome", uid)
            del dados["lives"]["streamers"][str(self.server_id)][uid]
            salvar_dados()
            await interaction.response.send_message(f"Streamer **{nome}** removido com sucesso!", ephemeral=True)
            try:
                embed = await self.parent_view.build_embed()
                await interaction.message.edit(embed=embed, view=self.parent_view)
            except: pass
        else:
            await interaction.response.send_message("Streamer não encontrado.", ephemeral=True)

class AddStreamerByLinkModal(Modal, title="Adicionar Streamer"):
    plataforma = TextInput(label="PLATAFORMA (twitch/youtube/kick/tiktok)", placeholder="Ex: twitch", required=True)
    username = TextInput(label="USERNAME DO STREAMER", placeholder="Ex: alanzoka, CHICOMG, @lordntj1478, youtube.com/@lordn", required=True)
    discord_user = TextInput(label="DISCORD DO STREAMER (opcional)", placeholder="ID ou @ do usuário", required=False)
    observacao = TextInput(label="OBSERVAÇÃO (mensagem padrão)", placeholder="Aparecerá na notificação da live", required=False)

    def __init__(self, server_id, parent_view):
        super().__init__()
        self.server_id = server_id
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        plat_input = self.plataforma.value.strip().lower()
        username_input = self.username.value.strip()
        obs = self.observacao.value.strip()

        extracted_plat, extracted_id = extract_platform_from_url(username_input)
        if extracted_plat and extracted_id:
            platform = extracted_plat
            identifier = extracted_id
            # Se não foi definido nome via Discord, usa o identifier como nome
            nome_streamer = identifier
        else:
            if plat_input not in ["twitch", "youtube", "kick", "tiktok"]:
                await interaction.response.send_message("Plataforma inválida. Escolha entre twitch, youtube, kick ou tiktok.", ephemeral=True)
                return
            platform = plat_input
            identifier = username_input
            nome_streamer = identifier

        uid = str(interaction.user.id)  # fallback
        if self.discord_user.value.strip():
            try:
                uid_str = self.discord_user.value.strip().replace("<@!","").replace("<@","").replace(">","")
                uid = str(int(uid_str))
                # Se Discord foi vinculado, usa o nome do membro
                member = interaction.guild.get_member(int(uid))
                if member:
                    nome_streamer = member.display_name
            except:
                pass

        if str(self.server_id) not in dados["lives"]["streamers"]:
            dados["lives"]["streamers"][str(self.server_id)] = {}
        if uid not in dados["lives"]["streamers"][str(self.server_id)]:
            dados["lives"]["streamers"][str(self.server_id)][uid] = {
                "nome": nome_streamer,
                "twitch": None,
                "youtube": None,
                "kick": None,
                "tiktok": None,
                "observacao": ""
            }

        dados["lives"]["streamers"][str(self.server_id)][uid][platform] = identifier
        dados["lives"]["streamers"][str(self.server_id)][uid]["nome"] = nome_streamer
        if obs:
            dados["lives"]["streamers"][str(self.server_id)][uid]["observacao"] = obs

        salvar_dados()
        await interaction.response.send_message(f"Streamer **{nome_streamer}** adicionado em **{platform}**!", ephemeral=True)
        try:
            embed = await self.parent_view.build_embed()
            await interaction.message.edit(embed=embed, view=self.parent_view)
        except: pass

# ========= PAINEL DE AÇÕES (com data e múltiplas prints) =========
class ActionPanelView(View):
    def __init__(self, server_id):
        super().__init__(timeout=None)
        self.server_id = server_id

    @discord.ui.button(label="Abrir Ação", style=discord.ButtonStyle.success, emoji="⚔️")
    async def open_action(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ActionModal(self.server_id))

    @discord.ui.button(label="Pagamento", style=discord.ButtonStyle.primary, emoji="💰")
    async def payment(self, interaction: discord.Interaction, button: Button):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores podem gerenciar pagamentos.", ephemeral=True); return
        server_actions = dados["acoes"].get(str(self.server_id), {})
        unpaid = {k: v for k, v in server_actions.items() if not v.get("pago", False)}
        if not unpaid:
            await interaction.response.send_message("Nenhuma ação pendente de pagamento.", ephemeral=True); return
        view = ActionSelectView(self.server_id, unpaid)
        await interaction.response.send_message("Selecione a ação:", view=view, ephemeral=True)

class ActionModal(Modal, title="Registrar Ação"):
    nome_acao = TextInput(label="Ação (nome do lugar)", placeholder="Ex: Assalto ao Banco Central", required=True)
    valor = TextInput(label="Valor (R$)", placeholder="Ex: 25000", required=True)
    resultado = TextInput(label="Vitória ou Derrota", placeholder="Digite Vitória ou Derrota", required=True)
    darkcoin = TextInput(label="Darkcoin", placeholder="Quantidade, 0 se não teve", required=True)
    data_acao = TextInput(label="Data da Ação (DD/MM/AAAA)", placeholder="Ex: 25/12/2025", required=True)

    def __init__(self, server_id):
        super().__init__()
        self.server_id = server_id

    async def on_submit(self, interaction: discord.Interaction):
        try: valor_num = float(self.valor.value.replace(",","."))
        except ValueError: await interaction.response.send_message("Valor inválido!", ephemeral=True); return
        try: dark_num = int(self.darkcoin.value)
        except ValueError: await interaction.response.send_message("Darkcoin inválida!", ephemeral=True); return
        result = self.resultado.value.strip().lower()
        if result not in ["vitória","derrota","vitoria"]:
            await interaction.response.send_message("Resultado deve ser 'Vitória' ou 'Derrota'.", ephemeral=True); return
        result = "Vitória" if result in ["vitória","vitoria"] else "Derrota"
        data_str = self.data_acao.value.strip()
        try:
            datetime.strptime(data_str, "%d/%m/%Y")
        except ValueError:
            await interaction.response.send_message("Data inválida! Use DD/MM/AAAA.", ephemeral=True); return
        self.action_info = {
            "nome_acao": self.nome_acao.value.strip(),
            "valor": valor_num,
            "resultado": result,
            "darkcoin": dark_num,
            "data_acao": data_str,
            "puxado_por": interaction.user.id
        }
        view = MemberSelectView(self.server_id, self.action_info)
        await interaction.response.send_message("Selecione os membros que participaram da ação:", view=view, ephemeral=True)

class MemberSelectView(View):
    def __init__(self, server_id, action_data):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.action_data = action_data
        self.selected_members = [action_data["puxado_por"]]

    @discord.ui.select(cls=UserSelect, placeholder="Selecione os membros...", min_values=1, max_values=25)
    async def select_members(self, interaction: discord.Interaction, select: UserSelect):
        self.selected_members = list(set([self.action_data["puxado_por"]] + [u.id for u in select.values]))
        await interaction.response.defer()

    @discord.ui.button(label="Confirmar e Enviar Print", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        if not self.selected_members:
            await interaction.response.send_message("Selecione pelo menos um membro.", ephemeral=True); return
        self.action_data["membros"] = self.selected_members
        await interaction.response.send_message(
            f"Membros selecionados: {len(self.selected_members)}. **Envie a primeira print da ação** (. Você pode enviar várias, uma por vez).",
            ephemeral=True
        )
        print_urls = []
        def check(m):
            return m.author == interaction.user and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        # Coleta múltiplas prints até que o usuário digite "pronto"
        await interaction.followup.send("Envie quantas prints quiser. Quando terminar, digite `pronto`.", ephemeral=True)
        while True:
            try:
                msg = await bot.wait_for('message', timeout=300.0, check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
                if msg.content.lower() == "pronto":
                    break
                if msg.attachments:
                    for att in msg.attachments:
                        if att.content_type and att.content_type.startswith('image/'):
                            print_urls.append(att.url)
                else:
                    await interaction.followup.send("Envie uma imagem ou digite `pronto`.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Tempo esgotado. As prints enviadas até agora serão salvas.", ephemeral=True)
                break
        self.action_data["print_urls"] = print_urls
        self.action_data["pago"] = False
        self.action_data["data_registro"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        action_id = str(int(datetime.now().timestamp()))
        dados["acoes"].setdefault(str(self.server_id), {})[action_id] = self.action_data
        salvar_dados()
        canal_logs = bot.get_channel(CANAL_ACOES_LOGS_ID)
        if canal_logs:
            embed = discord.Embed(title="NOVA AÇÃO REGISTRADA", color=discord.Color.green(), timestamp=datetime.now())
            embed.add_field(name="Ação", value=self.action_data["nome_acao"], inline=True)
            embed.add_field(name="Valor", value=f"R$ {self.action_data['valor']:,.2f}", inline=True)
            embed.add_field(name="Resultado", value=self.action_data["resultado"], inline=True)
            embed.add_field(name="Darkcoin", value=str(self.action_data["darkcoin"]), inline=True)
            embed.add_field(name="Data", value=self.action_data["data_acao"], inline=True)
            embed.add_field(name="Líder", value=f"<@{self.action_data['puxado_por']}>", inline=True)
            membros_str = " ".join(f"<@{m}>" for m in self.selected_members)
            embed.add_field(name="Participantes", value=membros_str, inline=False)
            if print_urls:
                embed.set_image(url=print_urls[0])
            await canal_logs.send(embed=embed)
        await interaction.followup.send("Ação registrada com sucesso!", ephemeral=True)
        self.stop()

class ActionSelectView(View):
    def __init__(self, server_id, actions):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.add_item(ActionDropdown(actions))

class ActionDropdown(Select):
    def __init__(self, actions):
        options = []
        for k, v in actions.items():
            nome = v.get("nome_acao", "Ação")
            valor = v.get("valor", 0)
            data = v.get("data_acao", "s/d")
            label = f"{nome[:40]} (R$ {valor:,.0f}) - {data}"
            options.append(discord.SelectOption(label=label[:100], value=k))
        super().__init__(placeholder="Escolha uma ação...", options=options)

    async def callback(self, interaction: discord.Interaction):
        action_id = self.values[0]
        action = dados["acoes"].get(str(interaction.guild_id), {}).get(action_id)
        if not action:
            await interaction.response.send_message("Ação não encontrada.", ephemeral=True); return
        valor = action["valor"]
        lavagem = valor * 0.25
        liquido = valor - lavagem
        n_membros = len(action["membros"])
        por_membro = liquido / n_membros if n_membros > 0 else 0
        embed = discord.Embed(title="RESUMO DO PAGAMENTO", color=discord.Color.orange())
        embed.add_field(name="Ação", value=action.get("nome_acao", "?"), inline=False)
        embed.add_field(name="Data", value=action.get("data_acao", "?"), inline=False)
        embed.add_field(name="Valor Total (Dinheiro Sujo)", value=f"R$ {valor:,.2f}", inline=False)
        embed.add_field(name="Lavagem (25%)", value=f"R$ {lavagem:,.2f}", inline=True)
        embed.add_field(name="Valor Líquido", value=f"R$ {liquido:,.2f}", inline=True)
        embed.add_field(name="Dividido por", value=f"{n_membros} membros", inline=True)
        embed.add_field(name="Cada membro recebe", value=f"R$ {por_membro:,.2f}", inline=True)
        view = ConfirmPaymentView(interaction.guild_id, action_id, liquido, por_membro, action["membros"])
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ConfirmPaymentView(View):
    def __init__(self, server_id, action_id, valor_liquido, valor_por_membro, membros):
        super().__init__(timeout=120)
        self.server_id = server_id
        self.action_id = action_id
        self.valor_liquido = valor_liquido
        self.valor_por_membro = valor_por_membro
        self.membros = membros

    @discord.ui.button(label="Confirmar Pagamento", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(
            "Envie as **prints dos comprovantes** (quantas quiser). Quando terminar, digite `pronto`.",
            ephemeral=True
        )
        print_urls = []
        def check(m): return m.author == interaction.user and m.channel == interaction.channel
        while True:
            try:
                msg = await bot.wait_for('message', timeout=300.0, check=check)
                if msg.content.lower() == "pronto":
                    break
                if msg.attachments:
                    for att in msg.attachments:
                        if att.content_type and att.content_type.startswith('image/'):
                            print_urls.append(att.url)
                else:
                    await interaction.followup.send("Envie uma imagem ou digite `pronto`.", ephemeral=True)
            except asyncio.TimeoutError:
                await interaction.followup.send("Tempo esgotado. As prints enviadas até agora serão salvas.", ephemeral=True)
                break
        action = dados["acoes"].get(str(self.server_id), {}).get(self.action_id)
        if action:
            action["pago"] = True
            action["pagamento"] = {
                "valor_liquido": self.valor_liquido,
                "valor_por_membro": self.valor_por_membro,
                "print_urls": print_urls,
                "data_pagamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "admin_id": interaction.user.id
            }
            salvar_dados()
            canal_logs = bot.get_channel(CANAL_ACOES_LOGS_ID)
            if canal_logs:
                embed = discord.Embed(title="PAGAMENTO DE AÇÃO", color=discord.Color.green(), timestamp=datetime.now())
                embed.add_field(name="Ação", value=action.get("nome_acao", "?"), inline=True)
                embed.add_field(name="Valor Líquido", value=f"R$ {self.valor_liquido:,.2f}", inline=True)
                embed.add_field(name="Por Membro", value=f"R$ {self.valor_por_membro:,.2f}", inline=True)
                embed.add_field(name="Admin", value=f"<@{interaction.user.id}>", inline=True)
                if print_urls: embed.set_image(url=print_urls[0])
                await canal_logs.send(embed=embed)
            await interaction.followup.send("Pagamento registrado com sucesso!", ephemeral=True)
        else:
            await interaction.followup.send("Erro: ação não encontrada.", ephemeral=True)
        self.stop()

# ========= EVENTOS =========
@bot.event
async def on_member_remove(member):
    if str(member.id) in dados["usuarios_banidos"]: return
    await log_admin("USUÁRIO SAIU", f"{member.mention} saiu. Iniciando limpeza...")
    await limpar_logs_usuario(member.id, member.name)
    if str(member.id) in dados["canais"]:
        canal = member.guild.get_channel(dados["canais"][str(member.id)])
        if canal:
            try: await canal.delete(reason=f"Usuário {member.name} saiu")
            except: pass
        del dados["canais"][str(member.id)]; salvar_dados()
    await log_admin("LIMPEZA CONCLUÍDA", f"{member.mention} removido do sistema.")

@bot.event
async def on_ready():
    print(f"Bot {bot.user} online!")
    live_check_loop.start()
    for guild in bot.guilds:
        canal_vendas = bot.get_channel(CHAT_COMPRA_VENDA_ID)
        if canal_vendas:
            async for msg in canal_vendas.history(limit=10):
                if msg.author == bot.user: await msg.delete()
            await canal_vendas.send(embed=discord.Embed(title="SISTEMA DE COMPRA E VENDA", description="💸 **Venda de Munição**\n🛒 **Compra de Produto**", color=discord.Color.blue()), view=CompraVendaView())
        categoria_painel = guild.get_channel(CATEGORIA_PAINEL_ID)
        if categoria_painel:
            canal_criar = discord.utils.get(categoria_painel.channels, name="criar-canal")
            if not canal_criar: canal_criar = await categoria_painel.create_text_channel("criar-canal")
            async for msg in canal_criar.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            await canal_criar.send(embed=discord.Embed(title="SISTEMA DE FARM", description="Clique no botão abaixo para criar seu canal privado!\n\n🔒 Apenas você e os administradores terão acesso", color=discord.Color.blue()), view=BotaoCriarCanalView())
        categoria_backup = guild.get_channel(CATEGORIA_BACKUP_ID)
        if categoria_backup:
            canal_backup = discord.utils.get(categoria_backup.channels, name="painel-backup")
            if not canal_backup: canal_backup = await categoria_backup.create_text_channel("painel-backup")
            async for msg in canal_backup.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            await canal_backup.send(embed=discord.Embed(title="💾 PAINEL DE BACKUP", description="💾 **Criar Backup**\n🗑️ **Apagar Backups**", color=discord.Color.blue()), view=BackupView())
        canal_acoes = bot.get_channel(CANAL_ACOES_PAINEL_ID)
        if canal_acoes:
            async for msg in canal_acoes.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            embed = discord.Embed(title="⚔️ PAINEL DE AÇÕES", description="Gerencie as ações e os pagamentos da facção.", color=discord.Color.dark_red())
            embed.add_field(name="Abrir Ação", value="Registre uma nova ação com valor, data, participantes e prints.", inline=False)
            embed.add_field(name="Pagamento", value="Efetue o pagamento das ações pendentes (apenas ADMs).", inline=False)
            view = ActionPanelView(guild.id)
            await canal_acoes.send(embed=embed, view=view)
        canal_lives = bot.get_channel(CANAL_LIVES_PAINEL_ID)
        if canal_lives:
            async for msg in canal_lives.history(limit=5):
                if msg.author == bot.user: await msg.delete()
            view = LiveConfigView(guild.id)
            embed = await view.build_embed()
            await canal_lives.send(embed=embed, view=view)
    await atualizar_ranking()
    await log_admin("🤖 BOT INICIADO", f"Bot {bot.user.mention} online!", 0x00ff00)

if __name__ == "__main__":
    carregar_dados()
    bot.run(TOKEN)