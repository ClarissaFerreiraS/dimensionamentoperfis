# Dimensionamento de Pilares — NBR 8800:2024

App desktop para dimensionamento à compressão de perfis de aço (laminados W/HP
e soldados CS), conforme **ABNT NBR 8800:2024**. Permite gerenciar um
catálogo de perfis e tipos de aço, salvar/editar projetos de dimensionamento,
gerar o memorial de cálculo em **PDF** e visualizar a **seção transversal
cotada** do perfil.

## Origem

A lógica de cálculo foi extraída, **sem alteração de fórmulas**, dos scripts
originais `Codigocompleto.py` e `CodigocomPDF.py` (mantidos no repositório,
intocados, como referência histórica). Esses scripts liam `ELU Compressão.xlsx`
diretamente e não guardavam nada entre execuções; o app novo (pasta `app/`)
substitui essa leitura posicional por um catálogo **SQLite** editável, com o
Excel como fonte de importação inicial (seed) e não mais como banco de dados
de trabalho.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Primeira execução — popular o catálogo

O catálogo (`catalogo.db`, criado na raiz do projeto, ignorado pelo git) começa
vazio. Para populá-lo a partir da planilha original, escolha uma das duas
formas:

**Via linha de comando:**

```bash
python -m app.importers.excel_importer "ELU Compressão.xlsx" catalogo.db
```

Essa carga deve ser feita antes de usar o app. Depois disso, os catálogos são
exibidos como dados fixos e somente para consulta.

## Rodando o app

```bash
python -m app.main
```

Abas disponíveis:

- **Projetos** — lista de projetos salvos (novo/duplicar/excluir); ao abrir
  ou editar um projeto, o formulário permite escolher aço, família e bitola,
  informar `Nc,Sd` e os parâmetros de flambagem (`Kx/Lx`, `Ky/Ly`, `Kz/Lz`,
  `Ea`/`Ga`), calcular o dimensionamento, visualizar a seção cotada e gerar o
  memorial em PDF.
- **Catálogo de Perfis** — tabelas fixas, somente para consulta, de perfis
  laminados e soldados.
- **Tipos de Aço** — tabela fixa, somente para consulta, de `fy`/`fu` por
  designação.

**Importante:** um projeto salvo guarda apenas os *dados de entrada* (perfil,
aço, cargas). O resultado (`Nc,Rd`, veredito etc.) é **recalculado toda vez
que o projeto é aberto**, a partir dos dados atuais do catálogo. Isso significa
que editar um perfil ou um tipo de aço no catálogo atualiza automaticamente
todos os projetos que os utilizam.

## Rodando os testes

```bash
pytest
```

`tests/test_calculations.py` é um teste de regressão que reproduz o caso
validado na própria planilha original (perfil W 310 x 21.0, aço ASTM A572
Grau 50) e confere que o motor de cálculo extraído chega exatamente aos
mesmos números (`Nc,Rd ≈ 626,76 kN`, aprovado).

## Arquitetura

```
app/
├── main.py              # bootstrap: abre o banco, abre a janela principal
├── db/                  # schema.sql (DDL) + conexão SQLite
├── domain/
│   ├── models.py         # dataclasses: SteelType, Profile, LoadCase, DesignResult
│   ├── calculations.py   # motor de cálculo puro (extraído dos scripts originais)
│   └── drawing.py        # build_section_scene(profile) — geometria em mm, sem UI
├── importers/            # leitura do Excel → SQLite
├── repositories.py        # CRUD (SteelType / Profile / Project) sobre o SQLite
├── report/                # geração do memorial em PDF (fpdf2)
└── ui/                    # PySide6: janela principal, editor de projeto,
                            # editores de catálogo, canvas da seção cotada
```

O ponto central da arquitetura é que **duas telas consomem a mesma geometria**:
`app/domain/drawing.py` gera uma `SectionScene` (retângulos e cotas em mm) de
forma totalmente independente de UI ou de PDF; `app/ui/section_canvas.py`
(`QPainter`) e `app/report/pdf_report.py` (`fpdf2`) apenas renderizam essa
mesma cena em contextos diferentes — a lógica geométrica nunca é duplicada.

### Nota sobre a nomenclatura do desenho

A referência visual fornecida pelo usuário foi um bloco dinâmico do AutoCAD
com cotas travadas rotuladas `W` (largura da mesa), `Wt` (espessura da alma),
`R` (raio de concordância), `Ft` (espessura da mesa) e altura total. O desenho
gerado por este app usa a nomenclatura da própria NBR 8800 (`bf`, `tw`, `r`,
`tf`, `d`) em vez dos nomes de parâmetro do bloco do AutoCAD, por serem os
termos usados no memorial de cálculo e no restante da norma. Essa é uma
suposição de design deliberada — se for preferível bater 1:1 com os rótulos
do bloco do AutoCAD, os rótulos podem ser trocados em um único lugar:
`app/domain/drawing.py`.
