"""
================================================================================
SOFTWARE UNIFICADO DE DIMENSIONAMENTO À COMPRESSÃO (ABNT NBR 8800:2024)
================================================================================
Suporta Perfis Laminados (W e HP) e Perfis Soldados (CS)
"""

import os                 # Interação com o sistema operacional (limpar tela )
import pandas as pd       # Manipulação de dados (leitura de arquivos Excel)
from pick import pick     # Biblioteca para criar menus interativos no terminal (escolha de perfil e material)
import math               # Funções matemáticas (cálculo de potências, raízes, etc.)  

# ==============================================================================
# 0. FUNÇÕES DE UTILIDADE E BLINDAGEM DE ERROS
# ==============================================================================
def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')    # Garante a limpeza da tela tanto no Windows quanto no Linux/Mac

""" 
Essa função lê a digitação do usuário e substitui vírgula por ponto.
Isso evita que o programa dê 'crash' caso o usuário digite 200,0 em vez de 200.0.
"""

def ler_numero(mensagem):
    while True:                                         # Loop infinito até que o usuário digite um número válido
        try:                                            # Função se "der errado" nas linhas abaixo, pula para o except e não dá 'crash' no programa
            valor = input(mensagem).replace(',', '.')   # Substitui vírgula por ponto
            return float(valor)
        except ValueError:                              # Se o valor digitado não for um número, exibe uma mensagem de erro e solicita a entrada novamente
            print("Erro: Por favor, digite apenas números válidos.")

# ==============================================================================
# 1. MENU RAIZ: ESCOLHA DA FAMÍLIA DO PERFIL
# ==============================================================================
arquivo_excel = 'ELU Compressão.xlsx'                   # Nome do arquivo Excel contendo os dados dos perfis e materiais

limpar_tela()                                           # Limpa a tela do terminal antes de exibir o menu principal
print("============================================================")
print(" SISTEMA DE DIMENSIONAMENTO DE PILARES (NBR 8800:2024)")
print("============================================================\n")

opcoes_familia = [                                      # Lista de opções para o menu de seleção da família do perfil
    "1 - Perfis Laminados Padrão (Série W e HP)",       # Opção 1: Perfis Laminados (W e HP)
    "2 - Perfis Soldados Montados (Série CS)" # Opção 2: Perfis Soldados (CS, VS, CVS)
]
escolha_familia, index_familia = pick(opcoes_familia, "PASSO 1: SELECIONE A FAMÍLIA DO PERFIL (Use a seta e aperte ENTER)", indicator='=>')  # Exibe o menu interativo para o usuário escolher a família do perfil 

is_laminado = (index_familia == 0)                      # Define a variável booleana 'is_laminado' como True se o usuário escolher a opção 1 (Perfis Laminados), caso contrário, será False (Perfis Soldados)

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
    b = v[2]           # Comprimento total da peça (do topo da mesa à base da alma)
    bf = v[3]
    tw = v[4]
    tf = v[5]
    d_linha = v[7]     # Trecho reto da alma (d')
    h = b - (2 * tf)   # Altura livre da alma entre mesas
    Ag, Ix, rx, Iy, ry = v[8], v[9], v[11], v[13], v[15]
    J, Cw = v[18], v[21]
else:
    b = v[3]           # Comprimento total da peça
    bf = v[7]
    tw = v[4]
    tf = v[6]
    h = v[5]           # Altura livre da alma entre mesas
    d_linha = h        # Para perfis soldados, d' é igual a h (não há raio de concordância)
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

λ0 = ((Ag * (fy / 10)) / Ne_min)**0.5

if λ0 <= 1.5:
    X = 0.658**(λ0**2)
else:
    X = 0.877 / (λ0**2)

# ==============================================================================
# 5. VERIFICAÇÃO DE FLAMBAGEM LOCAL (ÁREA EFETIVA BIFURCADA)
# ==============================================================================
sigma_c = X * fy  
b_mesa = bf / 2
bt_mesa = b_mesa / tf

if is_laminado:
    # LÓGICA PARA LAMINADOS
    limite_norma_mesa = 0.56 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_mesa = limite_norma_mesa / (X**0.5)
    c1_m, c2_m = 0.22, 1.49
    
    bt_alma = d_linha / tw
    limite_norma_alma = 1.49 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_alma = limite_norma_alma / (X**0.5)
    c1_a, c2_a = 0.18, 1.31
    kc = None
else:
    # LÓGICA PARA SOLDADOS
    bt_alma_para_kc = h / tw
    kc = 4.0 / (bt_alma_para_kc ** 0.5)
    kc = max(0.35, min(kc, 0.76)) # Delimita entre 0.35 e 0.76
    
    limite_norma_mesa = 0.64 * ((Ea * 1000 * kc) / fy)**0.5
    limite_efetivo_mesa = limite_norma_mesa / (X**0.5)
    c1_m, c2_m = 0.22, 1.49
    
    bt_alma = h / tw
    limite_norma_alma = 1.49 * ((Ea * 1000) / fy)**0.5
    limite_efetivo_alma = limite_norma_alma / (X**0.5)
    c1_a, c2_a = 0.18, 1.31

# --- Cálculo de bef (Mesa) ---
if bt_mesa > limite_efetivo_mesa:
    sigma_el_mesa = ((c2_m * limite_norma_mesa) / bt_mesa)**2 * fy
    bef_mesa = b_mesa * (1 - c1_m * (sigma_el_mesa / sigma_c)**0.5) * (sigma_el_mesa / sigma_c)**0.5
else:
    bef_mesa = b_mesa

# --- Cálculo de hef (Alma) ---
altura_ref_alma = d_linha if is_laminado else h
if bt_alma > limite_efetivo_alma:
    sigma_el_alma = ((c2_a * limite_norma_alma) / bt_alma)**2 * fy
    hef_alma = altura_ref_alma * (1 - c1_a * (sigma_el_alma / sigma_c)**0.5) * (sigma_el_alma / sigma_c)**0.5
else:
    hef_alma = altura_ref_alma

# Área Efetiva Final
perda_mesas = 4 * (b_mesa - bef_mesa) * tf
perda_alma = (altura_ref_alma - hef_alma) * tw
A_ef_cm2 = ((Ag * 100) - perda_mesas - perda_alma) / 100

# ==============================================================================
# 6. RELATÓRIO TÉCNICO (COM CARTÃO DE GEOMETRIA TIPO FTOOL)
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

# CARTÃO VISUAL DE GEOMETRIA (Estilo FTOOL)
print("GEOMETRIA DA SEÇÃO")
print(f"b : \t{b:<8.1f} mm \t bf: \t{bf:<8.1f} mm")
print(f"tw: \t{tw:<8.1f} mm \t tf: \t{tf:<8.1f} mm")
print(f"h : \t{h:<8.1f} mm \t d': \t{d_linha:<8.1f} mm")
print("-" * 60)

print("[1] ESBELTEZ E ESTABILIDADE GLOBAL")
print(f"Esbeltez eixo X (\u03BBx): \t{esbeltez_x:.2f}")
print(f"Esbeltez eixo Y (\u03BBy): \t{esbeltez_y:.2f}")

if esbeltez_max <= 200:
    print(f"Limite (\u03BB_max \u2264 200): \t[OK] Atende à Norma")
else:
    print(f"Limite (\u03BB_max \u2264 200): \t[FALHA] Peça muito esbelta!")

print("")
print(f"Carga Crítica Flexão (Nex): \t{Nex:.2f} kN")
print(f"Carga Crítica Flexão (Ney): \t{Ney:.2f} kN")
print(f"Carga Crítica Torção (Nez): \t{Nez:.2f} kN")
print(f"Carga Crítica Mínima (Ne_min): \t{Ne_min:.2f} kN")
print(f"Índice de esbeltez (\u03BB0): \t\t{λ0:.3f}")
print(f"Fator de redução (\u03C7): \t\t{X:.4f}")

print("-" * 60)
print("[2] FLAMBAGEM LOCAL (ÁREA EFETIVA)")

# --- MEMORIAL: MESA ---
print("Mesas (elementos AL)")
str_kc = f"  |  kc = {kc:.3f}" if not is_laminado else ""
print(f"b/t (bf/2.tf) = {bt_mesa:.2f}{str_kc}")

if is_laminado:
    print(f"(b/t)lim = 0,56 \u221A(Ea/fy) = {limite_norma_mesa:.2f}")
else:
    print(f"(b/t)lim = 0,64 \u221A(Ea.kc/fy) = {limite_norma_mesa:.2f}")

print(f"(b/t)lim / \u221A\u03C7 = {limite_efetivo_mesa:.2f}")

if bt_mesa > limite_efetivo_mesa:
    print("Logo, OCORRE flambagem local (Calcular bef)")
    print(f"c1 = {c1_m:.2f} | c2 = {c2_m:.2f} | \u03C3el = {sigma_el_mesa:.2f} MPa")
    print(f"\u221A(\u03C3el/\u03C7fy) = {(sigma_el_mesa / sigma_c)**0.5:.5f}")
    print(f"bef = {bef_mesa:.2f} mm | bef(adot.) = {min(bef_mesa, b_mesa):.2f} mm")
else:
    print("Logo, NÃO OCORRE flambagem local (Mesa compacta/semicompacta)")

print("- " * 30)

# --- MEMORIAL: ALMA ---
print("Alma (elemento AA)")
str_relacao = "d'/tw" if is_laminado else "h/tw"
print(f"b/t ({str_relacao}) = {bt_alma:.2f}")
print(f"(b/t)lim = 1,49 \u221A(Ea/fy) = {limite_norma_alma:.2f}")
print(f"(b/t)lim / \u221A\u03C7 = {limite_efetivo_alma:.2f}")

if bt_alma > limite_efetivo_alma:
    print("Logo, OCORRE flambagem local (Calcular bef)")
    print(f"c1 = {c1_a:.2f} | c2 = {c2_a:.2f} | \u03C3el = {sigma_el_alma:.2f} MPa")
    print(f"\u221A(\u03C3el/\u03C7fy) = {(sigma_el_alma / sigma_c)**0.5:.5f}")
    print(f"bef = {hef_alma:.2f} mm | bef(adot.) = {min(hef_alma, altura_ref_alma):.2f} mm")
else:
    print("Logo, NÃO OCORRE flambagem local (Alma compacta/semicompacta)")

print("- " * 30)
print(f"Área Bruta (Ag): \t\t{Ag:.2f} cm\u00B2")
print(f"Área efetiva (Aef): \t\t{A_ef_cm2:.2f} cm\u00B2")

print("-" * 60)
print("[3] RESULTADO DO DIMENSIONAMENTO")
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
    print(f" [✓] VERIFICAÇÃO: ATENDE AO DIMENSIONAMENTO. Taxa de trabalho: {((Nc_sd/Nc_Rd)*100):.1f}%")
elif Nc_Rd < Nc_sd:
    print(" [X] VERIFICAÇÃO: NÃO ATENDE AO DIMENSIONAMENTO. O esforço ultrapassa a capacidade.")
else:
    print(" [X] VERIFICAÇÃO: NÃO ATENDE AO DIMENSIONAMENTO. A esbeltez ultrapassa o limite.")
print("=" * 60 + "\n")