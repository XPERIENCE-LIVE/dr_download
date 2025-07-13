const js = require('@eslint/js');
const reactPlugin = require('eslint-plugin-react');
const globals = require('globals');

const sanitizedBrowser = Object.fromEntries(
  Object.entries(globals.browser).map(([k, v]) => [k.trim(), v])
);
const sanitizedNode = Object.fromEntries(
  Object.entries(globals.node).map(([k, v]) => [k.trim(), v])
);
const sanitizedJest = Object.fromEntries(
  Object.entries(globals.jest).map(([k, v]) => [k.trim(), v])
);

module.exports = [
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
  {
    files: ['**/__tests__/**/*.{js,jsx}', '**/*.test.{js,jsx}'],
    languageOptions: {
      globals: {
        ...sanitizedBrowser,
        ...sanitizedNode,
        ...sanitizedJest,
      },
    },
  },
];
