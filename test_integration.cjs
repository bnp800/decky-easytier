#!/usr/bin/env node
/**
 * Integration Test for Decky EasyTier Plugin
 * Validates frontend-backend API contract
 */

const fs = require('fs');
const path = require('path');

console.log('='.repeat(60));
console.log('Decky EasyTier Integration Tests');
console.log('='.repeat(60));

let testsPassed = 0;
let testsFailed = 0;

function test(name, condition, details = '') {
  if (condition) {
    console.log(`✓ ${name}`);
    if (details) console.log(`  ${details}`);
    testsPassed++;
  } else {
    console.log(`✗ ${name}`);
    if (details) console.log(`  ${details}`);
    testsFailed++;
  }
}

// Test 1: Configuration files validation
console.log('\n=== Configuration Files ===');

const pluginJson = JSON.parse(fs.readFileSync('plugin.json', 'utf8'));
test(
  'plugin.json has valid name',
  pluginJson.name && pluginJson.name.length > 0,
  `Name: ${pluginJson.name}`
);

test(
  'plugin.json has required fields',
  pluginJson.name && pluginJson.author && pluginJson.publish,
  'Has name, author, and publish fields'
);

const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));
test(
  'package.json has valid name',
  packageJson.name && packageJson.name.length > 0,
  `Name: ${packageJson.name}`
);

// Test 2: Build output validation
console.log('\n=== Build Output Validation ===');

test(
  'dist/index.js exists',
  fs.existsSync('dist/index.js'),
  'Frontend bundle exists'
);

test(
  'dist/index.js is not empty',
  fs.existsSync('dist/index.js') && fs.statSync('dist/index.js').size > 0,
  `Size: ${fs.statSync('dist/index.js').size} bytes`
);

// Test 3: API contract validation
console.log('\n=== API Contract Validation ===');

// Check Python backend for API methods
const mainPy = fs.readFileSync('main.py', 'utf8');
const apiMethods = [
  'get_combined_status',
  'install_easytier',
  'start_easytier',
  'stop_easytier',
  'save_plugin_settings'
];

apiMethods.forEach(method => {
  test(
    `Python backend has ${method} method`,
    mainPy.includes(`async def ${method}`) || mainPy.includes(`def ${method}`),
    `Method defined in main.py`
  );
});

// Check TypeScript frontend for API calls
const useEasyTierTs = fs.readFileSync('src/hooks/useEasyTier.ts', 'utf8');

apiMethods.forEach(method => {
  test(
    `TypeScript frontend calls ${method}`,
    useEasyTierTs.includes(`'${method}'`) || useEasyTierTs.includes(`"${method}"`),
    `API call defined in useEasyTier.ts`
  );
});

// Test 4: Event system validation
console.log('\n=== Event System Validation ===');

const events = [
  'service_status',
  'install_progress',
  'node_registered'
];

events.forEach(event => {
  // Check Python emits the event - check for both single and double quotes
  const pythonEmits = mainPy.includes(`"${event}"`) || mainPy.includes(`'${event}'`);

  // Check TypeScript listens to the event - check the addEventListener calls
  const typescriptListens = useEasyTierTs.includes(`addEventListener<[`) &&
                           useEasyTierTs.includes(`'${event}'`);

  test(
    `Event flow for ${event}`,
    pythonEmits && typescriptListens,
    `Python emits (${pythonEmits}) and TypeScript listens (${typescriptListens})`
  );
});

// Test 5: User interface validation
console.log('\n=== User Interface Validation ===');

const easyTierPanel = fs.readFileSync('src/components/EasyTierPanel.tsx', 'utf8');

const expectedStates = [
  'uninstalled',
  'stopped',
  'running',
  'partial',
  'error'
];

expectedStates.forEach(state => {
  test(
    `UI handles ${state} state`,
    easyTierPanel.includes(`'${state}'`) || easyTierPanel.includes(`"${state}"`),
    `State handled in EasyTierPanel.tsx`
  );
});

// Check for required UI components
const requiredComponents = [
  'DualStatusPanel',
  'PluginSettingsPanel',
  'QRCodeDisplay',
  'ErrorBanner'
];

requiredComponents.forEach(component => {
  test(
    `UI includes ${component}`,
    easyTierPanel.includes(component),
    `Component imported and used`
  );
});

// Test 6: Type definitions validation
console.log('\n=== Type Definitions Validation ===');

test(
  'types.ts exists',
  fs.existsSync('src/types.ts'),
  'Type definitions file exists'
);

if (fs.existsSync('src/types.ts')) {
  const typesTs = fs.readFileSync('src/types.ts', 'utf8');

  const requiredTypes = [
    'CombinedStatus',
    'PluginSettings',
    'ProcessStatus',
    'ApiResponse'
  ];

  requiredTypes.forEach(type => {
    test(
      `Type ${type} defined`,
      typesTs.includes(`interface ${type}`) || typesTs.includes(`type ${type}`),
      `Type definition found`
    );
  });
}

// Test 7: Resources and assets
console.log('\n=== Resources and Assets ===');

// Check for README
const readmeExists = fs.existsSync('README.md') || fs.existsSync('readme.md');
test('README file exists', readmeExists, 'Documentation present');

// Check for LICENSE
const licenseExists = fs.existsSync('LICENSE');
test('LICENSE file exists', licenseExists, 'License file present');

// Test 8: File structure validation
console.log('\n=== File Structure ===');

const expectedStructure = [
  'src/index.tsx',
  'src/hooks/useEasyTier.ts',
  'src/components/EasyTierPanel.tsx',
  'src/components/DualStatusPanel.tsx',
  'src/components/PluginSettingsPanel.tsx',
  'src/components/QRCodeDisplay.tsx',
  'main.py',
  'plugin.json',
  'package.json'
];

expectedStructure.forEach(file => {
  test(
    `File ${file} exists`,
    fs.existsSync(file),
    `Required file present`
  );
});

// Summary
console.log('\n' + '='.repeat(60));
console.log('Test Summary');
console.log('='.repeat(60));
console.log(`Total tests: ${testsPassed + testsFailed}`);
console.log(`✓ Passed: ${testsPassed}`);
console.log(`✗ Failed: ${testsFailed}`);
console.log('='.repeat(60));

if (testsFailed === 0) {
  console.log('🎉 All integration tests passed!');
  process.exit(0);
} else {
  console.log('❌ Some integration tests failed');
  process.exit(1);
}
