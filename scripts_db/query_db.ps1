param(
    [string]$Action = "tables",
    [string]$Sql,
    [string]$Table,
    [int]$Limit = 20,
    [string]$Status
)

$ScriptPath = Join-Path $PSScriptRoot "query_db.py"
$args = @($Action)

if ($Sql) { $args += "--sql"; $args += $Sql }
if ($Table) { $args += "--table"; $args += $Table }
if ($Limit -ne 20) { $args += "--limit"; $args += $Limit }
if ($Status) { $args += "--status"; $args += $Status }

python $ScriptPath @args
