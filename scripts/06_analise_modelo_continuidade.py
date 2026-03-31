import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

# ================================
# 1. CARREGAR BASE
# ================================

df = pd.read_csv("base_analitica_periodicos.csv")

# Garantir tipos
df["proporcao_doi"] = pd.to_numeric(df["proporcao_doi"], errors="coerce")
df["anos_com_indexacao"] = pd.to_numeric(df["anos_com_indexacao"], errors="coerce")
df["lacuna_maxima"] = pd.to_numeric(df["lacuna_maxima"], errors="coerce")

# remover NA críticos
df = df.dropna(subset=["proporcao_doi", "anos_com_indexacao", "lacuna_maxima", "zona_bradford"])

# ================================
# 2. CORRELAÇÃO (DOI × CONTINUIDADE)
# ================================

corr_anos = df["proporcao_doi"].corr(df["anos_com_indexacao"])
corr_lacuna = df["proporcao_doi"].corr(df["lacuna_maxima"])

print("\n=== CORRELAÇÕES ===")
print(f"DOI × anos_com_indexacao: {corr_anos:.4f}")
print(f"DOI × lacuna_maxima: {corr_lacuna:.4f}")

# ================================
# 3. MODELO 1 — CONTINUIDADE (REGRESSÃO)
# ================================

print("\n=== MODELO 1: anos_com_indexacao ~ DOI + Bradford ===")

modelo1 = smf.ols(
    "anos_com_indexacao ~ proporcao_doi + C(zona_bradford)",
    data=df
).fit()

print(modelo1.summary())

# ================================
# 4. MODELO 2 — LACUNA (INSTABILIDADE)
# ================================

print("\n=== MODELO 2: lacuna_maxima ~ DOI + Bradford ===")

modelo2 = smf.ols(
    "lacuna_maxima ~ proporcao_doi + C(zona_bradford)",
    data=df
).fit()

print(modelo2.summary())

# ================================
# 5. MODELO 3 — LOGÍSTICO (CONTINUANTE)
# ================================

print("\n=== MODELO 3: probabilidade de ser CONTINUANTE ===")

df["is_continuante"] = (df["categoria_continuidade"] == "continuante").astype(int)

modelo3 = smf.logit(
    "is_continuante ~ proporcao_doi + C(zona_bradford)",
    data=df
).fit()

print(modelo3.summary())
