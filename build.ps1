$IMAGE_NAME = "qumea-plugin"

# Version aus pyproject.toml lesen
$VERSION = python -c "import tomllib;print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"

Write-Host "Version: $VERSION"

# Docker Image bauen
docker build --pull --no-cache `
    -t ${IMAGE_NAME}:${VERSION} `
    -t ${IMAGE_NAME}:latest `
    .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed"
    exit 1
}

Write-Host "Build finished"

# Image exportieren
$TAR_FILE = "${IMAGE_NAME}-${VERSION}.tar"


docker save ${IMAGE_NAME}:${VERSION} -o $TAR_FILE

Write-Host "Image saved to $TAR_FILE"