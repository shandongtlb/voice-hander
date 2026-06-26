param(
    [Parameter(Mandatory = $true)]
    [string]$AudioPath,

    [string]$SessionId = "",

    [string]$BaseUrl = "http://127.0.0.1:18080",

    [string]$SaveReplyAudioTo = ""
)

$ErrorActionPreference = "Stop"

$ResolvedAudioPath = Resolve-Path $AudioPath
$audioBytes = [System.IO.File]::ReadAllBytes($ResolvedAudioPath)

$payload = @{
    audio_base64 = [System.Convert]::ToBase64String($audioBytes)
    filename = [System.IO.Path]::GetFileName($ResolvedAudioPath)
}

if ($SessionId -ne "") {
    $payload.session_id = $SessionId
}

$json = $payload | ConvertTo-Json -Depth 10
$body = [System.Text.Encoding]::UTF8.GetBytes($json)

$request = [System.Net.HttpWebRequest]::Create("$BaseUrl/v1/voice")
$request.Method = "POST"
$request.ContentType = "application/json; charset=utf-8"
$request.Accept = "application/json"
$request.ContentLength = $body.Length

$requestStream = $request.GetRequestStream()
$requestStream.Write($body, 0, $body.Length)
$requestStream.Close()

try {
    $response = $request.GetResponse()
    $responseStream = $response.GetResponseStream()
    $reader = [System.IO.StreamReader]::new($responseStream, [System.Text.Encoding]::UTF8)
    $responseText = $reader.ReadToEnd()
    $reader.Close()
    $response.Close()
}
catch [System.Net.WebException] {
    if ($_.Exception.Response -ne $null) {
        $responseStream = $_.Exception.Response.GetResponseStream()
        $reader = [System.IO.StreamReader]::new($responseStream, [System.Text.Encoding]::UTF8)
        $responseText = $reader.ReadToEnd()
        $reader.Close()
        $_.Exception.Response.Close()
        Write-Output $responseText
        exit 1
    }
    throw
}

if ($SaveReplyAudioTo -ne "") {
    $parsed = $responseText | ConvertFrom-Json
    if ($parsed.audio_base64 -ne $null -and $parsed.audio_base64 -ne "") {
        [System.IO.File]::WriteAllBytes($SaveReplyAudioTo, [System.Convert]::FromBase64String($parsed.audio_base64))
    }
}

Write-Output $responseText
