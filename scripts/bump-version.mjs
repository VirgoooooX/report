import { readFileSync, writeFileSync } from 'fs'
import { resolve, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = resolve(__dirname, '..')

const args = process.argv.slice(2)
const dryRun = args.includes('--dry-run')
const level = args.find(a => ['patch', 'minor', 'major'].includes(a)) || 'patch'

function readVersion(filePath) {
  const content = readFileSync(filePath, 'utf-8').trim()
  return content
}

function writeVersion(filePath, version) {
  if (!dryRun) writeFileSync(filePath, version + '\n')
}

function parseVersion(v) {
  const parts = v.split('.').map(Number)
  return { major: parts[0], minor: parts[1], patch: parts[2] }
}

function bump(version, level) {
  const v = parseVersion(version)
  if (level === 'major') { v.major++; v.minor = 0; v.patch = 0 }
  else if (level === 'minor') { v.minor++; v.patch = 0 }
  else { v.patch++ }
  return `${v.major}.${v.minor}.${v.patch}`
}

function updatePackageJson(v) {
  const pkgPath = resolve(root, 'frontend', 'package.json')
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8'))
  pkg.version = v
  if (!dryRun) writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')
}

const currentVersion = readVersion(resolve(root, 'VERSION'))
const nextVersion = bump(currentVersion, level)

if (dryRun) {
  console.log(`[dry-run] ${currentVersion} -> ${nextVersion} (${level})`)
} else {
  writeVersion(resolve(root, 'VERSION'), nextVersion)
  updatePackageJson(nextVersion)
  console.log(nextVersion)
}
