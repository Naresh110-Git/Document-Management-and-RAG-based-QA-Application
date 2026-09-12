Param(
    [string[]]$Args
)

$basedir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $basedir

# Ensure backend directory is on PYTHONPATH so imports like `from app...` resolve
$env:PYTHONPATH = $basedir

# Run pytest with any provided args
python -m pytest @Args
