#!/usr/bin/env bash
set -e

# Asegura que tenemos las últimas refs/tags
git fetch origin --tags

# ----------------------------------------------------
# FASE 1: CREAR NUEVA VERSIÓN EN 'qa'
# ----------------------------------------------------
echo "=== FASE 1: CREACIÓN DE NUEVO RELEASE EN 'qa' ==="

# 1) Detectar cambios
CHANGED=$(git status --short)
if [ -z "$CHANGED" ]; then
  echo "⚠️ No hay cambios detectados para el commit."
  read -rp "❓ ¿Desea continuar e intentar promocionar la ÚLTIMA versión de 'qa' a 'prod'? (y/n): " SKIP_COMMIT
  if [ "$SKIP_COMMIT" = "y" ]; then
    COMMIT_MSG="[Salto de commit]"
    # --- LÍNEA CORREGIDA ---
    # Busca la última etiqueta en todo el repositorio, la ordena y selecciona la más reciente.
    BASE_TAG=$(git tag -l 'v*.*.*' --sort=-v:refname | head -n 1)
    NEW_TAG=$BASE_TAG
    echo "Saltando commit. La versión a promocionar será $BASE_TAG."
    goto_promotion=true
  else
    echo "❌ Operación cancelada."
    exit 1
  fi
fi

if [ -z "$goto_promotion" ]; then
  # 2) Mensaje de commit
  read -rp "📝 Escribe el mensaje de commit para 'qa': " COMMIT_MSG

  # 3) --- LÍNEA CORREGIDA ---
  # Obtiene la última etiqueta de forma fiable, listando y ordenando todas las existentes.
  BASE_TAG=$(git tag -l 'v*.*.*' --sort=-v:refname | head -n 1)
  if [ -z "$BASE_TAG" ]; then
    # Si no hay ninguna etiqueta en el repositorio, empezamos en v1.0.0
    BASE_TAG="v1.0.0"
  fi
  BASE_NUM=${BASE_TAG#v}
  IFS='.' read -r MAJOR MINOR PATCH <<<"$BASE_NUM"

  # 4) Preguntar por el tipo de incremento
  echo ""
  echo "Tipo de incremento actual (base: $BASE_TAG):"
  echo "  1) Patch (vX.Y.Z+1) - Correcciones de errores pequeñas"
  echo "  2) Minor (vX.Y+1.0) - Nuevas funcionalidades"
  echo "  3) Major (vX+1.0.0) - Cambios incompatibles"
  echo ""
  read -rp "❓ Selecciona el tipo de incremento (1, 2, o 3): " INCREMENT_TYPE

  # 5) Calcular el nuevo tag
  NEW_MAJOR=$MAJOR
  NEW_MINOR=$MINOR
  NEW_PATCH=$PATCH

  case "$INCREMENT_TYPE" in
      1)
          NEW_PATCH=$((PATCH + 1))
          ;;
      2)
          NEW_MINOR=$((MINOR + 1))
          NEW_PATCH=0
          ;;
      3)
          NEW_MAJOR=$((MAJOR + 1))
          NEW_MINOR=0
          NEW_PATCH=0
          ;;
      *)
          echo "❌ Tipo de incremento no válido. Operación cancelada."
          exit 1
          ;;
  esac

  NEW_TAG="v${NEW_MAJOR}.${NEW_MINOR}.${NEW_PATCH}"

  # 6) Resumen y Confirmación de la Fase 1
  echo ""
  echo "🚀 Resumen de Release en 'qa':"
  echo "   Archivos a commitear:"
  echo "$CHANGED" | sed 's/^/     • /'
  echo "   Branch destino: qa"
  echo "   Commit:         $COMMIT_MSG"
  echo "   Base (qa):    $BASE_TAG"
  echo "   Nuevo tag:      $NEW_TAG"
  echo ""
  read -rp "❓ ¿Proceder con el COMMIT y TAG en 'qa'? (y/n): " CONFIRM_QA
  [ "$CONFIRM_QA" = "y" ] || { echo "❌ Operación cancelada."; exit 1; }

  # 7) Ejecutar pipeline de qa
  git add .
  git commit -m "$COMMIT_MSG" || echo "⚠️ No hay cambios que commitear"
  git push origin qa

  git tag "$NEW_TAG"
  git push origin "$NEW_TAG"

  echo "✅ Commit y tag $NEW_TAG publicados correctamente (branch qa)."
  echo ""
fi

# ----------------------------------------------------
# FASE 2: PROMOCIÓN DE 'qa' A 'prod'
# ----------------------------------------------------
echo "=== FASE 2: PROMOCIÓN A PRODUCCIÓN ==="
read -rp "⭐ ¿Desea promocionar la versión $NEW_TAG (de 'qa') a la rama 'prod'? (y/n): " PROMOTE_PROD

if [ "$PROMOTE_PROD" = "y" ]; then
    echo "Procesando promoción de $NEW_TAG a 'prod'..."
    git checkout qa
    git pull origin qa
    git checkout prod
    git pull origin prod

    if git merge --no-ff qa -m "Merge branch 'qa' for Production Release $NEW_TAG"; then
        echo "✅ Merge de 'qa' a 'prod' completado."

        PROD_TAG="prod-$NEW_TAG"
        echo "   Nuevo tag de Producción: $PROD_TAG"
        git tag "$PROD_TAG"
        git push origin prod
        git push origin "$PROD_TAG"
        echo "🎉 ¡Éxito! La versión $NEW_TAG ha sido promocionada a 'prod' y etiquetada como $PROD_TAG."
    else
        echo "❌ Falló el merge de 'qa' a 'prod'. Revise y resuelva los conflictos manualmente."
        exit 1
    fi
    git checkout qa
else
    echo "▶️ No se solicitó la promoción a 'prod'. Proceso de release finalizado en 'qa'."
fi