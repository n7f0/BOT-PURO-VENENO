import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import asyncio
from datetime import datetime
import json
import os
import sys

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

def salvar_dados():
    with open("dados_bot.json", "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

def carregar_dados():
    try:
        with open("dados_bot.json", "r", encoding="utf-8") as f:
            dados.update(json.load(f))
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
        registro = {"produtos":produtos,"data":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"print_url":imagem_url,"validado":True,"farm_id":len(dados["usuarios"][str(self.user_id)]["farms"])+1}
        dados["usuarios"][str(self.user_id)]["farms"].append(registro)
        salvar_dados()
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
        # Correção da linha 270
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

# ========= NOVO FechamentoCaixaModal (sem campo Farm Sujo, com Observação) =========
class FechamentoCaixaModal(Modal, title="Fechamento de Caixa da Semana"):
    meta_farm = TextInput(label="Meta de Farm (Sim/Não)", placeholder="Digite Sim ou Não", required=True)
    salario = TextInput(label="Salário (R$)", placeholder="Ex: 1000", required=True)
    extra = TextInput(label="Extra (R$)", placeholder="Ex: 200", required=True)
    total = TextInput(label="Total (R$)", placeholder="Ex: 4700", required=True)
    observacao = TextInput(label="Observação (mensagem carinhosa)", placeholder="Deixe uma mensagem para o usuário...", required=False, style=discord.TextStyle.long)

    def __init__(self, user_id, user_name, canal):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
        self.canal = canal

    async def on_submit(self, interaction: discord.Interaction):
        if not is_admin(interaction.user):
            await interaction.response.send_message("Apenas administradores!", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=True)

        meta = self.meta_farm.value.strip().lower()
        if meta not in ["sim","não","nao"]:
            await interaction.followup.send("Meta de Farm deve ser 'Sim' ou 'Não'!", ephemeral=True); return
        meta = "Sim" if meta=="sim" else "Não"

        try:
            salario_valor = float(self.salario.value.replace(",","."))
            extra_valor = float(self.extra.value.replace(",","."))
            total_valor = float(self.total.value.replace(",","."))
        except ValueError:
            await interaction.followup.send("Valores inválidos!", ephemeral=True); return

        # Obtém automaticamente o dinheiro sujo acumulado
        sujo = dados["usuarios"].get(str(self.user_id), {}).get("dinheiro_sujo", 0.0)

        # Verifica se a soma confere
        if abs((sujo + salario_valor + extra_valor) - total_valor) > 0.01:
            await interaction.followup.send(
                f"O total informado (R$ {total_valor:,.2f}) não confere com a soma do Farm Sujo (R$ {sujo:,.2f}) + Salário + Extra. Corrija.",
                ephemeral=True
            ); return

        await interaction.followup.send("📸 Agora envie a **print do comprovante** aqui no canal.", ephemeral=True)
        def check(m): return m.author==interaction.user and m.channel==self.canal and m.attachments and any(a.content_type and a.content_type.startswith('image/') for a in m.attachments)
        try: msg = await bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError: await interaction.followup.send("Tempo esgotado!", ephemeral=True); return
        imagem_url = msg.attachments[0].url

        valor_pagamento = salario_valor + extra_valor
        obs = self.observacao.value.strip() if self.observacao.value else None

        if str(self.user_id) not in dados["usuarios"]:
            dados["usuarios"][str(self.user_id)] = {"farms":[],"pagamentos":[],"nome":self.user_name,"dinheiro_sujo":0}

        dados["usuarios"][str(self.user_id)]["pagamentos"].append({
            "valor": valor_pagamento,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "admin": interaction.user.id,
            "admin_nome": interaction.user.name,
            "tipo": "Fechamento de Caixa Semanal",
            "salario": salario_valor,
            "extra": extra_valor,
            "farm_sujo": sujo,
            "meta_farm": meta,
            "print_url": imagem_url,
            "observacao": obs
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
            "total": total_valor,
            "valor_pago": valor_pagamento,
            "print_url": imagem_url,
            "observacao": obs
        }

        if str(self.user_id) not in dados["caixa_semana"]:
            dados["caixa_semana"][str(self.user_id)] = []
        dados["caixa_semana"][str(self.user_id)].append(fechamento)
        salvar_dados()

        # Notificação ao usuário
        try:
            user = await interaction.client.fetch_user(int(self.user_id))
            notif = discord.Embed(title="FECHAMENTO DE CAIXA", description=f"Registrado para {self.user_name}!", color=discord.Color.orange())
            notif.add_field(name="Meta de Farm", value=meta, inline=False)
            notif.add_field(name="Farm Sujo", value=f"R$ {sujo:,.2f}", inline=True)
            notif.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
            notif.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
            notif.add_field(name="Total", value=f"R$ {total_valor:,.2f}", inline=True)
            notif.add_field(name="Total Recebido", value=f"R$ {valor_pagamento:,.2f}", inline=True)
            if obs: notif.add_field(name="💌 Mensagem", value=obs, inline=False)
            notif.set_image(url=imagem_url)
            await user.send(embed=notif)
        except: pass

        # Embed no canal
        embed = discord.Embed(title="FECHAMENTO DE CAIXA SEMANAL", description=f"**{self.user_name}** fechou o caixa!", color=discord.Color.orange(), timestamp=datetime.now())
        embed.add_field(name="Meta de Farm", value=meta, inline=False)
        embed.add_field(name="Farm Sujo", value=f"R$ {sujo:,.2f}", inline=True)
        embed.add_field(name="Salário", value=f"R$ {salario_valor:,.2f}", inline=True)
        embed.add_field(name="Extra", value=f"R$ {extra_valor:,.2f}", inline=True)
        embed.add_field(name="TOTAL BRUTO", value=f"R$ {total_valor:,.2f}", inline=True)
        embed.add_field(name="PAGAMENTO REALIZADO", value=f"R$ {valor_pagamento:,.2f}", inline=True)
        embed.add_field(name="Responsável", value=interaction.user.mention, inline=False)
        if obs: embed.add_field(name="💌 Mensagem", value=obs, inline=False)
        embed.set_image(url=imagem_url)
        await self.canal.send(embed=embed)

        canal_registros = bot.get_channel(LOG_REGISTROS_ID)
        if canal_registros: await canal_registros.send(embed=embed)

        await interaction.followup.send(f"Fechamento de caixa registrado! Pagamento de R$ {valor_pagamento:,.2f} realizado.", ephemeral=True)
        await log_acao("fechar_caixa", interaction.user, f"Usuário: {self.user_name}\nMeta: {meta}\nPagamento: R$ {valor_pagamento}", 0xffa500)
        await log_admin("FECHAMENTO DE CAIXA", f"Usuário: {self.user_name}\nAdmin: {interaction.user.mention}\nTotal Pago: R$ {valor_pagamento:,.2f}", 0xffa500)
        await atualizar_ranking()

# ... (restante do código permanece igual, incluindo modais de compra/venda, views, eventos, etc.)