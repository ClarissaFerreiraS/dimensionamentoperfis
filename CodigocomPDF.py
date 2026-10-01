"""
================================================================================
SOFTWARE UNIFICADO DE DIMENSIONAMENTO À COMPRESSÃO (ABNT NBR 8800:2024)
================================================================================
Suporta Perfis Laminados (W e HP) e Perfis Soldados (CS)
"""

import os
import pandas as pd
from pick import pick
import math

# ==============================================================================
# 0. FUNÇÕES DE UTILIDADE E BLINDAGEM DE ERROS
# ==============================================================================
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def ler_numero(mensagem):
    while True:
        try:
            valor = input(mensagem).replace(',', '.')
            return float(valor)
        except ValueError:
            print("Erro: Por favor, digite apenas números válidos.")

# ==============================================================================
# 1. MENU RAIZ: IDENTIFICAÇÃO E ESCOLHA DA FAMÍLIA DO PERFIL
# ==============================================================================
arquivo_excel = 'ELU Compressão.xlsx'

limpar_tela()
print("============================================================")
print(" SISTEMA DE DIMENSIONAMENTO DE PILARES (NBR 8800:2024)")
print("============================================================\n")

nome_autor = input("Digite o nome do Autor / Engenheiro(a) para o PDF: ").strip()
if not nome_autor:
    nome_autor = "Engenheiro(a) Responsavel"

opcoes_familia = [
    "1 - Perfis Laminados Padrão (Série W e HP)",
    "2 - Perfis Soldados Montados (Série CS)"
]
escolha_familia, index_familia = pick(opcoes_familia, "PASSO 1: SELECIONE A FAMÍLIA DO PERFIL (Use a seta e aperte ENTER)", indicator='=>')

is_laminado = (index_familia == 0)

# ==============================================================================
# 2. CARREGAMENTO DO BANCO DE DADOS (DINÂMICO)
# ==============================================================================
limpar_tela()
print("Carregando banco de dados. Aguarde um momento...")

try:
    nome_aba = 'Perfis W e HP' if is_laminado else 'PerfilCS'
    dw = pd.read_excel(arquivo_excel, sheet_name=nome_aba, header=4)
    
    coluna_perfil = 'BITOLA\nmm x kg/m' if is_laminado else dw.columns[0]
    dicionario_perfis = {}

    for _, linha in dw.iterrows():
        nome_perfil = str(linha[coluna_perfil]).strip()
        if nome_perfil != 'nan' and pd.notna(linha[coluna_perfil]) and any(c.isdigit() for c in nome_perfil):
            dicionario_perfis[nome_perfil.upper()] = linha.to_dict()

    if not dicionario_perfis:
        raise ValueError(f"Nenhum perfil encontrado na aba '{nome_aba}'.")

    df_acos = pd.read_excel(arquivo_excel, sheet_name='Tipos de aço', header=1)
    dicionario_acos = {}

    for _, linha in df_acos.iterrows():
        nome_aco = str(linha['Designação']).strip()
        if nome_aco != 'nan' and pd.notna(linha['Designação']):
            dicionario_acos[nome_aco.upper()] = {
                'fy': float(linha['Tensão de escoamento, fy (MPa)']),
                'fu': float(linha['Tensão última, fu (MPa)'])
            }

except Exception as e:
    print(f"\n[ERRO CRÍTICO] Falha ao ler a planilha: {e}")
    exit()

# ==============================================================================
# 3. ENTRADA DE DADOS: PERFIL, MATERIAL E ESFORÇOS
# ==============================================================================
limpar_tela()
perfil_escolhido, _ = pick(list(dicionario_perfis.keys()), "PASSO 2: SELECIONE A BITOLA DO PERFIL", indicator='=>')
perfil_encontrado = dicionario_perfis[perfil_escolhido]

limpar_tela()
aco_escolhido, _ = pick(list(dicionario_acos.keys()), "PASSO 3: SELECIONE O MATERIAL DO AÇO", indicator='=>')
fy = dicionario_acos[aco_escolhido]['fy']
v = list(perfil_encontrado.values())

# --- EXTRAÇÃO GEOMÉTRICA DINÂMICA ---
if is_laminado:
    b = v[2]
    bf = v[3]
    tw = v[4]
    tf = v[5]
    d_linha = v[7]
    h = b - (2 * tf)
    Ag, Ix, rx, Iy, ry = v[8], v[9], v[11], v[13], v[15]
    J, Cw = v[18], v[21]
else:
    b = v[3]
    bf = v[7]
    tw = v[4]
    tf = v[6]
    h = v[5]
    d_linha = h
    Ag, Ix, rx, Iy, ry = v[2], v[8], v[10], v[12], v[14]
    J, Cw = v[17], v[18]

# --- DIGITAÇÃO DOS ESFORÇOS ---
limpar_tela()
print("=" * 60)
print(" PASSO 4: DADOS DE ESFORÇOS E COMPRIMENTOS DE FLAMBAGEM")
print("=" * 60)

Ea = ler_numero("Módulo de elasticidade Ea em GPa : ")
Ga = ler_numero("Módulo de elasticidade transversal Ga em GPa : ")
Nc_sd = ler_numero("Força axial de compressão solicitante Nc,Sd em kN : ")

print("\n--- FLAMBAGEM EM X (FLEXÃO) ---")
Kx = ler_numero("Fator de comprimento efetivo Kx (Adotar: 1.0): ")
Lx = ler_numero("Comprimento destravado Lx em metros: ")

print("\n--- FLAMBAGEM EM Y (FLEXÃO) ---")
Ky = ler_numero("Fator de comprimento efetivo Ky (Adotar: 1.0): ")
Ly = ler_numero("Comprimento destravado Ly em metros: ")

print("\n--- FLAMBAGEM EM Z (TORÇÃO) ---")
Kz = ler_numero("Fator de comprimento efetivo Kz (Adotar: 1.0): ")
Lz = ler_numero("Comprimento destravado Lz em metros: ")

# ==============================================================================
# 4. ESTABILIDADE GLOBAL E ESBELTEZ (NBR 8800:2024)
# ==============================================================================
esbeltez_x = (Kx * Lx * 100) / rx
esbeltez_y = (Ky * Ly * 100) / ry
esbeltez_max = max(esbeltez_x, esbeltez_y)

r0 = ((rx**2) + (ry**2))**0.5

Nex = ((math.pi**2) * (Ea * 100) * Ix) / ((Kx * Lx * 100)**2)
Ney = ((math.pi**2) * (Ea * 100) * Iy) / ((Ky * Ly * 100)**2)
Nez = 1 / (r0**2) * ((math.pi**2 * (Ea * 100) * Cw) / (Kz * Lz * 100)**2 + (Ga * 100) * J)

Ne_min = min(Nex, Ney, Nez)

lambda0_val = ((Ag * (fy / 10)) / Ne_min)**0.5

if lambda0_val <= 1.5:
    X = 0.658**(lambda0_val**2)
else:
    X = 0.877 / (lambda0_val**2)

# ==============================================================================
# 5. VERIFICAÇÃO DE FLAMBAGEM LOCAL (ÁREA EFETIVA BIFURCADA)
# ==============================================================================
sigma_c = X * fy  
b_mesa = bf / 2
bt_mesa = b_mesa / tf

if is_laminado:
    limite_norma_mesa = 0.56 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_mesa = limite_norma_mesa / (X**0.5)
    c1_m, c2_m = 0.22, 1.49
    
    bt_alma = d_linha / tw
    limite_norma_alma = 1.49 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_alma = limite_norma_alma / (X**0.5)
    c1_a, c2_a = 0.18, 1.31
    kc = None
else:
    bt_alma_para_kc = h / tw
    kc = 4.0 / (bt_alma_para_kc ** 0.5)
    kc = max(0.35, min(kc, 0.76)) 
    
    limite_norma_mesa = 0.64 * ((Ea * 1000 * kc) / fy)**0.5
    limite_efetivo_mesa = limite_norma_mesa / (X**0.5)
    c1_m, c2_m = 0.22, 1.49
    
    bt_alma = h / tw
    limite_norma_alma = 1.49 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_alma = limite_norma_alma / (X**0.5)
    c1_a, c2_a = 0.18, 1.31

# --- Cálculo de bef (Mesa) ---
ocorre_flamb_mesa = False
sigma_el_mesa = 0.0
raiz_termo_mesa = 0.0
if bt_mesa > limite_efetivo_mesa:
    ocorre_flamb_mesa = True
    sigma_el_mesa = ((c2_m * limite_norma_mesa) / bt_mesa)**2 * fy
    raiz_termo_mesa = (sigma_el_mesa / sigma_c)**0.5
    bef_mesa = b_mesa * (1 - c1_m * raiz_termo_mesa) * raiz_termo_mesa
else:
    bef_mesa = b_mesa

# --- Cálculo de bef (Alma) ---
altura_ref_alma = d_linha if is_laminado else h
ocorre_flamb_alma = False
sigma_el_alma = 0.0
raiz_termo_alma = 0.0
if bt_alma > limite_efetivo_alma:
    ocorre_flamb_alma = True
    sigma_el_alma = ((c2_a * limite_norma_alma) / bt_alma)**2 * fy
    raiz_termo_alma = (sigma_el_alma / sigma_c)**0.5
    bef_alma = altura_ref_alma * (1 - c1_a * raiz_termo_alma) * raiz_termo_alma
else:
    bef_alma = altura_ref_alma

# Área Efetiva Final
perda_mesas = 4 * (b_mesa - bef_mesa) * tf
perda_alma = (altura_ref_alma - bef_alma) * tw
A_ef_cm2 = ((Ag * 100) - perda_mesas - perda_alma) / 100

# ==============================================================================
# 6. RELATÓRIO TÉCNICO (TERMINAL)
# ==============================================================================
gama_a1 = 1.10
Nc_Rd = (X * A_ef_cm2 * (fy / 10)) / gama_a1

limpar_tela()
print("=" * 60)
print(" MEMÓRIA DE CÁLCULO: COMPRESSÃO NBR 8800:2024")
print("=" * 60)
print(f"Tipo   : {'Laminado' if is_laminado else 'Soldado'}")
print(f"Perfil : {perfil_escolhido}")
print(f"Aço    : {aco_escolhido} (fy = {fy} MPa)")
print("-" * 60)

print("GEOMETRIA DA SEÇÃO TRANSVERSAL")
print(f"b : \t{b:<8.1f} mm \t bf: \t{bf:<8.1f} mm")
print(f"tw: \t{tw:<8.1f} mm \t tf: \t{tf:<8.1f} mm")
print(f"h : \t{h:<8.1f} mm \t d': \t{d_linha:<8.1f} mm")
print("-" * 60)

print("[1] ESTABILIDADE GLOBAL")
print(f"Carga Crítica Flexão (Nex): \t{Nex:.2f} kN")
print(f"Carga Crítica Flexão (Ney): \t{Ney:.2f} kN")
print(f"Carga Crítica Torção (Nez): \t{Nez:.2f} kN")
print(f"Carga Crítica Mínima (Ne_min): \t{Ne_min:.2f} kN")
print(f"Índice de esbeltez (\u03BB0): \t\t{lambda0_val:.3f}")
print(f"Fator de redução (\u03C7): \t\t{X:.4f}")
print("-" * 60)

print("[2] VERIFICAÇÃO DO LIMITE DE ESBELTEZ")
print(f"Esbeltez em X (lambda_x) = {esbeltez_x:.2f}")
print(f"Esbeltez em Y (lambda_y) = {esbeltez_y:.2f}")
print(f"Esbeltez Maxima (lambda_max) = {esbeltez_max:.2f}")
print(f"Limite de esbeltez = 200.00")
if esbeltez_max <= 200:
    print("-> STATUS: ATENDE AO LIMITE DE ESBELTEZ (lambda_max <= 200)")
else:
    print("-> STATUS: NÃO ATENDE AO LIMITE DE ESBELTEZ (lambda_max > 200)")
print("-" * 60)

print("[3] FLAMBAGEM LOCAL (ÁREA EFETIVA)")

# --- MEMORIAL: MESA ---
print("Mesas (elementos AL)")
str_kc = f"  |  kc = {kc:.3f}" if not is_laminado else ""
print(f"b/t (bf/2.tf) = {bt_mesa:.2f}{str_kc}")

if is_laminado:
    print(f"(b/t)lim = 0,56 \u221A(Ea/fy) = {limite_norma_mesa:.2f}")
else:
    print(f"(b/t)lim = 0,64 \u221A(Ea.kc/fy) = {limite_norma_mesa:.2f}")

print(f"(b/t)lim / \u221A\u03C7 = {limite_efetivo_mesa:.2f}")

if ocorre_flamb_mesa:
    print("-> STATUS: OCORRE flambagem local na mesa.")
    print(f"c1 = {c1_m:.2f} | c2 = {c2_m:.2f} | sigma_el = {sigma_el_mesa:.2f} MPa")
    print(f"bef = {bef_mesa:.2f} mm | bef(adotado) = {min(bef_mesa, b_mesa):.2f} mm")
else:
    print("-> STATUS: NÃO ocorre flambagem local na mesa.")
    print(f"bef(adotado) = {min(bef_mesa, b_mesa):.2f} mm")

print("- " * 30)

# --- MEMORIAL: ALMA ---
print("Alma (elemento AA)")
str_relacao = "d'/tw" if is_laminado else "h/tw"
print(f"b/t ({str_relacao}) = {bt_alma:.2f}")
print(f"(b/t)lim = 1,49 \u221A(Ea/fy) = {limite_norma_alma:.2f}")
print(f"(b/t)lim / \u221A\u03C7 = {limite_efetivo_alma:.2f}")

if ocorre_flamb_alma:
    print("-> STATUS: OCORRE flambagem local na alma.")
    print(f"c1 = {c1_a:.2f} | c2 = {c2_a:.2f} | sigma_el = {sigma_el_alma:.2f} MPa")
    print(f"bef = {bef_alma:.2f} mm | bef(adotado) = {min(bef_alma, altura_ref_alma):.2f} mm")
else:
    print("-> STATUS: NÃO ocorre flambagem local na alma.")
    print(f"bef(adotado) = {min(bef_alma, altura_ref_alma):.2f} mm")

print("- " * 30)
print(f"Área Bruta (Ag): \t\t{Ag:.2f} cm\u00B2")
print(f"Área efetiva (Aef): \t\t{A_ef_cm2:.2f} cm\u00B2")

print("-" * 60)
print("[4] RESULTADO DO DIMENSIONAMENTO")
print(f"Esforço Resistente de Cálculo (Nc,Rd): \t{Nc_Rd:.2f} kN")
print(f"Esforço Solicitante (Nc,Sd) informado: \t{Nc_sd:.2f} kN")

print("\nVerificação:")
if Nc_sd < Nc_Rd:
    print("    Nc,Sd \t<\t Nc,Rd \t\t OK")
elif Nc_sd == Nc_Rd:
    print("    Nc,Sd \t=\t Nc,Rd \t\t OK")
else:
    print("    Nc,Sd \t>\t Nc,Rd \t\t NÃO OK")

print("\n" + "=" * 60)
if Nc_Rd >= Nc_sd and esbeltez_max <= 200:
    print(" [✓] VERIFICAÇÃO: ATENDE AO DIMENSIONAMENTO")
elif Nc_Rd < Nc_sd:
    print(" [X] VERIFICAÇÃO: NÃO ATENDE AO DIMENSIONAMENTO. O esforço ultrapassa a capacidade.")
else:
    print(" [X] VERIFICAÇÃO: NÃO ATENDE AO DIMENSIONAMENTO. A esbeltez ultrapassa o limite.")
print("=" * 60 + "\n")


# ==============================================================================
# 7. GERAÇÃO DO PDF (ESTRUTURA DETALHADA E IDÊNTICA AO TERMINAL)
# ==============================================================================
print("Gerando memorial de cálculo em PDF...\n")

try:
    from fpdf import FPDF

    class RelatorioPDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 11)
            self.set_fill_color(240, 243, 246)
            self.cell(0, 8, 'MEMORIAL DE CÁLCULO ESTRUTURAL - COMPRESSÃO PURA', border=1, ln=1, align='C', fill=True)
            self.set_font('Arial', '', 9)
            self.cell(0, 5, f'Autor(a) responsável: {nome_autor}', border='LR', ln=1)
            self.cell(0, 5, 'Norma de referência: ABNT NBR 8800:2024', border='LRB', ln=1)
            self.ln(3)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    pdf = RelatorioPDF()
    fonte_matematica = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'arial.ttf')
    if not os.path.isfile(fonte_matematica):
        raise FileNotFoundError(f'Fonte necessária para símbolos matemáticos não encontrada: {fonte_matematica}')
    pdf.add_font('ArialMath', '', fonte_matematica, uni=True)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    def add_secao(titulo):
        pdf.ln(4)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(20, 40, 100)
        pdf.set_draw_color(150, 155, 160)
        pdf.cell(0, 6, titulo, border='B', ln=1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def add_linha(texto, fonte='Arial'):
        pdf.set_font(fonte, '', 9)
        pdf.cell(0, 5, texto, ln=1)

    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 7, f"Perfil: {perfil_escolhido} ({'laminado' if is_laminado else 'soldado'}) | Aço: {aco_escolhido} (fy = {fy} MPa)", ln=1)
    
    add_secao("GEOMETRIA DA SEÇÃO TRANSVERSAL")
    largura_util = pdf.w - pdf.l_margin - pdf.r_margin
    espacamento_grupos = 7
    largura_colunas = largura_util - espacamento_grupos
    larguras = (
        largura_colunas * 0.16,
        largura_colunas * 0.22,
        largura_colunas * 0.37,
        largura_colunas * 0.25,
    )
    linhas_geometria = (
        ('b', f'{b:.1f} mm', 'Área bruta (Ag)', f'{Ag:.2f} cm²'),
        ('bf', f'{bf:.1f} mm', 'Momento de inércia em X (Ix)', f'{Ix:.2f} cm⁴'),
        ('tw', f'{tw:.1f} mm', 'Momento de inércia em Y (Iy)', f'{Iy:.2f} cm⁴'),
        ('tf', f'{tf:.1f} mm', 'Raio de giração em X (rx)', f'{rx:.2f} cm'),
        ('h', f'{h:.1f} mm', 'Raio de giração em Y (ry)', f'{ry:.2f} cm'),
        ("d'", f'{d_linha:.1f} mm', 'Raio de giração polar (r0)', f'{r0:.2f} cm'),
    )

    pdf.set_x(pdf.l_margin)
    pdf.set_font('Arial', 'B', 7.5)
    pdf.set_text_color(90, 98, 108)
    pdf.cell(larguras[0], 6, 'SÍMBOLO', align='L')
    pdf.cell(larguras[1], 6, 'DIMENSÃO', align='R')
    pdf.set_x(pdf.l_margin + larguras[0] + larguras[1] + espacamento_grupos)
    pdf.cell(larguras[2], 6, 'PROPRIEDADE GEOMÉTRICA', align='L')
    pdf.cell(larguras[3], 6, 'VALORES', align='R', ln=1)

    pdf.set_draw_color(178, 184, 191)
    pdf.set_line_width(0.25)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_text_color(35, 39, 44)
    pdf.set_font('ArialMath', '', 8.5)
    for dim_nome, dim_valor, prop_nome, prop_valor in linhas_geometria:
        pdf.set_x(pdf.l_margin)
        pdf.set_font('Arial', 'B', 8.5)
        pdf.cell(larguras[0], 7, dim_nome)
        pdf.set_font('Arial', '', 8.5)
        pdf.cell(larguras[1], 7, dim_valor, align='R')
        pdf.set_x(pdf.l_margin + larguras[0] + larguras[1] + espacamento_grupos)
        pdf.cell(larguras[2], 7, prop_nome)
        pdf.cell(larguras[3], 7, prop_valor, align='R', ln=1)
        pdf.set_draw_color(220, 223, 227)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())

    pdf.ln(4)
    pdf.set_font('Arial', 'B', 7.5)
    pdf.set_text_color(90, 98, 108)
    pdf.cell(0, 5, 'SEÇÃO TRANSVERSAL COTADA', ln=1, align='C')
    pdf.set_text_color(0, 0, 0)

    max_dim = max(b, bf)
    scale = 40.0 / max_dim
    s_b = b * scale
    s_bf = bf * scale
    s_tw = max(tw * scale, 0.5)
    s_tf = max(tf * scale, 0.5) 

    cx = pdf.w / 2
    py = pdf.get_y() + 2
    px = cx - s_bf / 2

    pdf.set_fill_color(200, 210, 230)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.3)
    pdf.rect(px, py, s_bf, s_tf, 'DF')
    pdf.rect(px, py + s_b - s_tf, s_bf, s_tf, 'DF')
    pdf.rect(cx - s_tw / 2, py + s_tf, s_tw, s_b - 2*s_tf, 'DF')
    pdf.set_line_width(0.2)
    pdf.set_y(py + s_b + 4)
    pdf.ln(4)

    # --------------------------------------------------------------------------
    # [1] ESTABILIDADE GLOBAL
    # --------------------------------------------------------------------------
    add_secao("1. ESTABILIDADE GLOBAL")
    
    add_linha(f"Carga crítica de flexão no eixo X (Nex): {Nex:.2f} kN")
    add_linha(f"Carga crítica de flexão no eixo Y (Ney): {Ney:.2f} kN")
    add_linha(f"Carga crítica de torção (Nez): {Nez:.2f} kN")
    add_linha(f"Carga crítica mínima (Ne,min): {Ne_min:.2f} kN")
    add_linha(f"Índice de esbeltez (λ0): {lambda0_val:.3f}", 'ArialMath')
    add_linha(f"Fator de redução (χ): {X:.4f}", 'ArialMath')

    # --------------------------------------------------------------------------
    # [2] VERIFICAÇÃO DO LIMITE DE ESBELTEZ
    # --------------------------------------------------------------------------
    add_secao("2. VERIFICAÇÃO DO LIMITE DE ESBELTEZ")
    
    add_linha(f"Esbeltez em X (λx) = {esbeltez_x:.2f}", 'ArialMath')
    add_linha(f"Esbeltez em Y (λy) = {esbeltez_y:.2f}", 'ArialMath')
    add_linha(f"Esbeltez máxima (λmax) = {esbeltez_max:.2f}", 'ArialMath')
    add_linha(f"Limite de esbeltez = 200.00")
    
    if esbeltez_max <= 200:
        mensagem_esbeltez = (
            f"ATENDE: λmax = {esbeltez_max:.2f} não ultrapassa o limite de 200.00."
        )
        pdf.set_fill_color(246, 249, 246)
        pdf.set_text_color(65, 88, 70)
        borda_esbeltez = 0
    else:
        mensagem_esbeltez = (
            f"NÃO ATENDE: λmax = {esbeltez_max:.2f} ultrapassa o limite de 200.00."
        )
        pdf.set_fill_color(252, 235, 235)
        pdf.set_draw_color(195, 90, 90)
        pdf.set_text_color(150, 35, 35)
        borda_esbeltez = 1
    pdf.set_font('ArialMath', '', 9)
    pdf.multi_cell(0, 7, mensagem_esbeltez, border=borda_esbeltez, fill=True)
    pdf.set_text_color(0, 0, 0)

    # --------------------------------------------------------------------------
    # [3] FLAMBAGEM LOCAL (AREA EFETIVA)
    # --------------------------------------------------------------------------
    if pdf.get_y() + 115 > pdf.h - pdf.b_margin:
        pdf.add_page()
    add_secao("3. FLAMBAGEM LOCAL")

    largura_util = pdf.w - pdf.l_margin - pdf.r_margin
    espacamento_colunas = 8
    largura_coluna = (largura_util - espacamento_colunas) / 2
    x_esquerda = pdf.l_margin
    x_direita = x_esquerda + largura_coluna + espacamento_colunas
    y_inicio = pdf.get_y() + 2
    str_rel_alma_pdf = "d'/tw" if is_laminado else "h/tw"

    def adicionar_coluna(x, titulo, relacao, bt, limite, limite_efetivo, ocorre, b, c1, c2, sigma_el, bef):
        pdf.set_xy(x, y_inicio)
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(largura_coluna, 6, titulo, ln=1)
        linhas = [
            f"b/t → ({relacao}) = {bt:.2f}",
            f"(b/t)_lim = {limite:.2f}",
            f"(b/t)_lim / √χ = {limite_efetivo:.2f}",
        ]
        if ocorre:
            linhas.extend((
                "Ocorre flambagem local.",
                f"c1 = {c1:.2f}    c2 = {c2:.2f}",
                f"σel = {sigma_el:.2f} MPa",
                f"bef = {bef:.2f} mm",
                f"bef(adotado) = {min(bef, b):.2f} mm",
            ))
        else:
            linhas.extend(("Não ocorre flambagem local.", f"b = bef = {b:.2f} mm"))
        pdf.set_font('ArialMath', '', 8.5)
        pdf.set_xy(x, y_inicio + 6)
        pdf.multi_cell(largura_coluna, 5, "\n".join(linhas))
        return pdf.get_y()

    y_mesa = adicionar_coluna(
        x_esquerda, "Mesas (elementos AL)", "bf/(2.tf)", bt_mesa,
        limite_norma_mesa, limite_efetivo_mesa, ocorre_flamb_mesa, b_mesa,
        c1_m, c2_m, sigma_el_mesa, bef_mesa,
    )
    y_alma = adicionar_coluna(
        x_direita, "Alma (elemento AA)", str_rel_alma_pdf, bt_alma,
        limite_norma_alma, limite_efetivo_alma, ocorre_flamb_alma, altura_ref_alma,
        c1_a, c2_a, sigma_el_alma, bef_alma,
    )

    pdf.set_y(max(y_mesa, y_alma) + 4)
    pdf.set_font('Arial', '', 8.5)
    pdf.cell(0, 6, f"Área efetiva (Aef) = {A_ef_cm2:.2f} cm²", ln=1)

    # --------------------------------------------------------------------------
    # [4] RESULTADO DO DIMENSIONAMENTO
    # --------------------------------------------------------------------------
    add_secao("4. RESULTADO DO DIMENSIONAMENTO")
    add_linha(f"Esforço resistente de cálculo (Nc,Rd): {Nc_Rd:.2f} kN")
    add_linha(f"Esforço solicitante informado (Nc,Sd): {Nc_sd:.2f} kN")

    resistencia_atende = Nc_sd <= Nc_Rd
    operador_resistencia = "≤" if resistencia_atende else ">"
    pdf.ln(2)
    pdf.set_font('ArialMath', '', 9)
    pdf.cell(0, 6, f"Nc,Sd = {Nc_sd:.2f} kN {operador_resistencia} Nc,Rd = {Nc_Rd:.2f} kN", ln=1)
    pdf.set_font('Arial', 'B', 9)
    if resistencia_atende:
        pdf.set_text_color(25, 105, 50)
        pdf.cell(0, 6, "ATENDE À RESISTÊNCIA", ln=1)
    else:
        pdf.set_text_color(150, 35, 35)
        pdf.cell(0, 6, "NÃO ATENDE À RESISTÊNCIA", ln=1)
    pdf.set_text_color(0, 0, 0)

    pdf.ln(3)
    pdf.set_font('Arial', 'B', 10)
    if Nc_Rd >= Nc_sd and esbeltez_max <= 200:
        mensagem_verificacao = "VERIFICAÇÃO: ATENDE AO DIMENSIONAMENTO"
        pdf.set_text_color(25, 105, 50)
    else:
        mensagem_verificacao = "VERIFICAÇÃO: NÃO ATENDE AO DIMENSIONAMENTO"
        pdf.set_text_color(150, 35, 35)
    pdf.set_draw_color(150, 155, 160)
    pdf.set_fill_color(240, 243, 246)
    pdf.cell(0, 11, mensagem_verificacao, border=1, ln=1, align='C', fill=True)
    pdf.set_text_color(0, 0, 0)

    nome_arquivo = f"Memorial_Compressao_{perfil_escolhido.replace('/', '_')}.pdf"
    pdf.output(nome_arquivo)
    print(f"[SUCESSO] Memorial de cálculo em PDF gerado e salvo como: '{nome_arquivo}'")

except Exception as e:
    print(f"\n[AVISO] Erro ao gerar o arquivo PDF: {e}")