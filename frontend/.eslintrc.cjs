module.exports = {
  root: true,
  env: { 
    browser: true, 
    es2020: true,
    node: true,
    jest: true
  },
  extends: [
    'eslint:recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'no-unused-vars': 'off',
    'no-redeclare': 'off',
    'no-undef': 'off',
  },
  globals: {
    'process': 'readonly',
    '__dirname': 'readonly',
    'GeolocationPosition': 'readonly',
    'describe': 'readonly',
    'it': 'readonly',
    'expect': 'readonly',
    'screen': 'readonly',
    'History': 'readonly',
    'Notification': 'readonly',
  },
}
