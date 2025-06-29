import js from '@eslint/js';
import reactPlugin from 'eslint-plugin-react';
import globals from 'globals';

const sanitizedBrowser = Object.fromEntries(
  Object.entries(globals.browser).map(([k, v]) => [k.trim(), v])
);
const sanitizedNode = Object.fromEntries(
  Object.entries(globals.node).map(([k, v]) => [k.trim(), v])
);

export default [
  {
    ignores: ['dist/**', 'node_modules/**'],
  },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...sanitizedBrowser,
        ...sanitizedNode,
      },
    },
    plugins: {
      react: reactPlugin,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
    },
  },
];
