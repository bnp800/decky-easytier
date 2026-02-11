#!/usr/bin/env node
/**
 * Frontend Code Quality Test for Decky EasyTier Plugin
 * Performs static analysis on TypeScript source files
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const SRC_DIR = 'src';

// Color output helpers
const colors = {
  green: (text) => `\x1b[32m${text}\x1b[0m`,
  red: (text) => `\x1b[31m${text}\x1b[0m`,
  yellow: (text) => `\x1b[33m${text}\x1b[0m`,
  blue: (text) => `\x1b[34m${text}\x1b[0m`,
};

function countFiles(dir, extension) {
  const files = fs.readdirSync(dir, { recursive: true });
  return files.filter(f => f.endsWith(extension)).length;
}

function checkFileExists(filepath) {
  const exists = fs.existsSync(filepath);
  console.log(exists ? colors.green(`✓ ${filepath} exists`) : colors.red(`✗ ${filepath} missing`));
  return exists;
}

function checkBuildOutput() {
  console.log('\n=== Build Output Check ===');
  const distExists = checkFileExists('dist/index.js');
  if (distExists) {
    const stats = fs.statSync('dist/index.js');
    const sizeKB = (stats.size / 1024).toFixed(2);
    console.log(colors.green(`✓ Build size: ${sizeKB} KB`));
    return sizeKB < 1000; // Should be less than 1MB
  }
  return false;
}

function analyzeSourceFiles() {
  console.log('\n=== Source File Analysis ===');

  const tsxFiles = countFiles(SRC_DIR, '.tsx');
  const tsFiles = countFiles(SRC_DIR, '.ts');

  console.log(colors.green(`✓ ${tsxFiles} TSX files`));
  console.log(colors.green(`✓ ${tsFiles} TypeScript files`));

  // Check for common patterns
  const patterns = {
    'React Hooks': /use[A-Z][a-zA-Z]+/,
    'API calls': /await callable|callable\(/,
    'Event listeners': /addEventListener/,
    'TypeScript interfaces': /interface\s+[A-Z]/,
  };

  console.log('\n=== Code Pattern Analysis ===');
  for (const [name, pattern] of Object.entries(patterns)) {
    const grepCmd = `grep -r "${pattern.source}" ${SRC_DIR} --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l`;
    try {
      const count = execSync(grepCmd, { encoding: 'utf8' }).trim();
      if (count > 0) {
        console.log(colors.green(`✓ ${name}: ${count} occurrences`));
      }
    } catch (e) {
      // Ignore errors
    }
  }

  return true;
}

function checkForCommonIssues() {
  console.log('\n=== Common Issues Check ===');

  const issues = [
    {
      name: 'console.log statements',
      pattern: /console\.log\(/,
      allowed: true, // Allowed in development
    },
    {
      name: 'TODO/FIXME comments',
      pattern: /TODO|FIXME/,
      allowed: true,
    },
    {
      name: 'any type usage',
      pattern: /:\s*any\s*[,>]/,
      allowed: false,
    },
    {
      name: 'unused imports',
      pattern: /^import.*\n(?!.*\b\w+\b)/m,
      allowed: false,
    },
  ];

  let hasIssues = false;
  for (const issue of issues) {
    const grepCmd = `grep -r "${issue.pattern.source}" ${SRC_DIR} --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l`;
    try {
      const count = execSync(grepCmd, { encoding: 'utf8' }).trim();
      if (count > 0) {
        const msg = `${issue.name}: ${count} found`;
        if (issue.allowed) {
          console.log(colors.yellow(`⚠ ${msg}`));
        } else {
          console.log(colors.red(`✗ ${msg}`));
          hasIssues = true;
        }
      }
    } catch (e) {
      // Ignore errors
    }
  }

  return !hasIssues;
}

function runTests() {
  console.log(colors.blue('=' .repeat(60)));
  console.log(colors.blue('Decky EasyTier Frontend Quality Tests'));
  console.log(colors.blue('=' .repeat(60)));

  let allPassed = true;

  // Check build output
  allPassed &= checkBuildOutput();

  // Analyze source files
  allPassed &= analyzeSourceFiles();

  // Check for common issues
  allPassed &= checkForCommonIssues();

  // Summary
  console.log('\n' + colors.blue('=' .repeat(60)));
  if (allPassed) {
    console.log(colors.green('✓ All frontend quality checks passed!'));
  } else {
    console.log(colors.red('✗ Some quality checks failed'));
  }
  console.log(colors.blue('=' .repeat(60)));

  return allPassed;
}

if (require.main === module) {
  process.exit(runTests() ? 0 : 1);
}

module.exports = { runTests };
