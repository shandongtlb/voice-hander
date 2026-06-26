param(
    [Parameter(Mandatory = $true)]
    [string]$Message,

    [string]$SessionId = "",

    [string]$BaseUrl = "http://127.0.0.1:18080"
)

$payload = @{
    message = $Message
}

if ($SessionId -ne "") {
    $payload.session_id = $SessionId
}

$json = $payload | ConvertTo-Json -Depth 10
$body = [System.Text.Encoding]::UTF8.GetBytes($json)

$request = [System.Net.HttpWebRequest]::Create("$BaseUrl/v1/chat")
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
    $reader.ReadToEnd()
    $reader.Close()
    $response.Close()
}
catch [System.Net.WebException] {
    if ($_.Exception.Response -ne $null) {
        $responseStream = $_.Exception.Response.GetResponseStream()
        $reader = [System.IO.StreamReader]::new($responseStream, [System.Text.Encoding]::UTF8)
        $reader.ReadToEnd()
        $reader.Close()
        $_.Exception.Response.Close()
    }
    else {
        throw
    }
}
