#!/usr/bin/env bash
# Install git hooks for branch policy enforcement.
# Run once after cloning: bash scripts/install-hooks.sh

HOOK_DIR="$(git rev-parse --git-dir)/hooks"
mkdir -p "$HOOK_DIR"

cat > "$HOOK_DIR/pre-push" << 'HOOK'
#!/usr/bin/env bash
# Prevents pushing feature branches that were created from main instead of development.

current_branch=$(git symbolic-ref --short HEAD 2>/dev/null)

# Skip checks for main, master, development, and CI branches (claude/*)
if [[ "$current_branch" == "main" || "$current_branch" == "master" || "$current_branch" == "development" || "$current_branch" == claude/* ]]; then
  exit 0
fi

# Check if development branch exists locally
if ! git rev-parse --verify development >/dev/null 2>&1; then
  echo "⚠️  Warning: 'development' branch not found locally."
  echo "   Please fetch it: git fetch origin development && git checkout development"
  exit 0
fi

# Verify the current branch is based on development, not main
merge_base_dev=$(git merge-base development "$current_branch" 2>/dev/null)
merge_base_main=$(git merge-base main "$current_branch" 2>/dev/null || git merge-base master "$current_branch" 2>/dev/null)

if [[ -n "$merge_base_main" && -n "$merge_base_dev" ]]; then
  # If branch point is closer to main than development, warn
  dev_distance=$(git rev-list --count "$merge_base_dev".."$current_branch" 2>/dev/null || echo 999)
  main_distance=$(git rev-list --count "$merge_base_main".."$current_branch" 2>/dev/null || echo 999)

  is_on_dev=$(git merge-base --is-ancestor "$merge_base_dev" development 2>/dev/null && echo "yes" || echo "no")

  if [[ "$is_on_dev" == "no" ]]; then
    echo "❌ ERROR: Branch '$current_branch' appears to be based on 'main', not 'development'."
    echo ""
    echo "   All feature and bugfix branches must be created from 'development'."
    echo "   To fix this:"
    echo "     git checkout development"
    echo "     git checkout -b $current_branch"
    echo "     git cherry-pick <your-commits>"
    echo ""
    echo "   Or rebase onto development:"
    echo "     git rebase --onto development main $current_branch"
    echo ""
    exit 1
  fi
fi

exit 0
HOOK

chmod +x "$HOOK_DIR/pre-push"
echo "✅ Git hooks installed successfully."
echo "   - pre-push: Enforces branch-from-development policy"
