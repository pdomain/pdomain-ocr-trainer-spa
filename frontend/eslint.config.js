// Flat ESLint config for the SPA.
//
// Canonical workspace config (2026-05-24):
//   - typescript-eslint strictTypeChecked + stylisticTypeChecked
//     (type-aware rules; requires parserOptions.projectService = true)
//   - react-hooks recommended (rules-of-hooks + exhaustive-deps)
//   - react-refresh (only-export-components warning for HMR sanity)
//   - eslint-config-prettier last, to disable any rules that would
//     fight Prettier's formatting decisions
//
// NOTE: failOnWarnings (--max-warnings 0) is left for a future pass
// after all existing warnings are resolved.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import jsxA11y from "eslint-plugin-jsx-a11y";
import eslintConfigPrettier from "eslint-config-prettier";
import globals from "globals";

export default tseslint.config(
  {
    // Test files and tooling config are excluded from type-aware linting.
    // tsconfig.json excludes test files from compilation (they use vitest-
    // only patterns that tsc can't check correctly). ESLint respects this
    // boundary — type safety in test files is enforced by vitest's
    // ts-jest/vite-plugin-checker setup, not ESLint.
    ignores: [
      "dist/**",
      "node_modules/**",
      "src/**/*.test.{ts,tsx}",
      "src/test/**",
      "eslint.config.js",
    ],
  },
  js.configs.recommended,
  // strictTypeChecked supersedes recommended and adds type-aware rules.
  // stylisticTypeChecked adds stylistic type-aware rules (consistent-type-
  // imports, etc.) that Prettier doesn't cover.
  // Scoped to src/**/*.{ts,tsx} so type-aware rules don't fire on
  // vite.config.ts / vitest.config.ts / other tooling files.
  ...tseslint.configs.strictTypeChecked.map((c) => ({
    ...c,
    files: ["src/**/*.{ts,tsx}"],
  })),
  ...tseslint.configs.stylisticTypeChecked.map((c) => ({
    ...c,
    files: ["src/**/*.{ts,tsx}"],
  })),
  // jsx-a11y: accessibility lint for JSX. Scoped to src/**/*.tsx only.
  // Existing code has some a11y violations; downgrade to warn so CI stays
  // green while they are addressed incrementally.
  {
    ...jsxA11y.flatConfigs.recommended,
    files: ["src/**/*.tsx"],
    rules: {
      ...jsxA11y.flatConfigs.recommended.rules,
      // All violations fixed; promote to error.
      "jsx-a11y/click-events-have-key-events": "error",
      "jsx-a11y/no-noninteractive-element-interactions": "error",
      "jsx-a11y/no-noninteractive-tabindex": "error",
      "jsx-a11y/no-redundant-roles": "error",
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      parserOptions: {
        // Type-aware linting: resolve types from the project's tsconfig.
        // Test files are excluded from ESLint via the top-level ignores
        // (matching tsconfig.json's exclude list).
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
      globals: {
        ...globals.browser,
        process: "readonly",
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // react-refresh: non-component exports moved to sibling .ts files.
      "react-refresh/only-export-components": [
        "error",
        { allowConstantExport: true },
      ],
      "no-unused-vars": "off",
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/restrict-template-expressions": [
        "error",
        { allowNumber: true, allowBoolean: true },
      ],
      "@typescript-eslint/no-confusing-void-expression": "off",
      "@typescript-eslint/prefer-nullish-coalescing": "off",
      "@typescript-eslint/consistent-type-assertions": [
        "error",
        { assertionStyle: "as" },
      ],
      "@typescript-eslint/no-unnecessary-condition": "error",
      // no-non-null-assertion: all violations fixed (null check + throw pattern).
      "@typescript-eslint/no-non-null-assertion": "error",
      "@typescript-eslint/no-empty-function": "warn",
      "@typescript-eslint/require-await": "warn",
      "@typescript-eslint/no-misused-promises": [
        "error",
        { checksVoidReturn: { attributes: false } },
      ],
      "@typescript-eslint/no-unsafe-assignment": "warn",
      "@typescript-eslint/no-unsafe-member-access": "warn",
      "@typescript-eslint/no-unsafe-argument": "warn",
      "@typescript-eslint/no-unsafe-call": "warn",
      "@typescript-eslint/no-unsafe-return": "warn",
      // no-deprecated: All JSX.Element usages replaced with React.JSX.Element.
      // ActiveJob false-positive (pdomain-ui JSDoc) suppressed inline.
      "@typescript-eslint/no-deprecated": "error",
      // no-invalid-void-type: void in union types (e.g. Promise<void | T>)
      // is a common API-shape pattern in the query layer. Downgrade to warn.
      "@typescript-eslint/no-invalid-void-type": "warn",
      // no-misused-spread: new rule in typescript-eslint 8.x; fires on
      // legitimate {...queryParams, ...extraParams} patterns where one
      // operand is an array from URLSearchParams. Downgrade to warn.
      "@typescript-eslint/no-misused-spread": "warn",
      // array-type: existing code mixes T[] and Array<T>; let it be for now.
      "@typescript-eslint/array-type": "off",
      // no-unnecessary-type-assertion: all violations fixed.
      "@typescript-eslint/no-unnecessary-type-assertion": "error",
      // no-base-to-string: all violations fixed via type narrowing.
      "@typescript-eslint/no-base-to-string": "error",
      // no-dynamic-delete: one deliberate usage for cache invalidation;
      // suppressed inline with rationale comment.
      "@typescript-eslint/no-dynamic-delete": "error",
      // no-unnecessary-type-conversion: String(x) where x is already a
      // string — existing pattern in template helpers and error formatting.
      "@typescript-eslint/no-unnecessary-type-conversion": "warn",
      // prefer-optional-chain: all violations fixed.
      "@typescript-eslint/prefer-optional-chain": "error",
    },
  },
  // Must come last: turns off any stylistic ESLint rule that would
  // conflict with Prettier's formatting.
  eslintConfigPrettier,
);
