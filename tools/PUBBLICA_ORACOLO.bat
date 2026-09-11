@echo off
setlocal
rem ===================================================================
rem  Oracolo del Sovrano + la consegna del 04/09 -> ANTEPRIMA su Vercel
rem  Origine protetta: Claudio Terzi [CT-LGAI-001].
rem
rem  Si lancia dalla radice di questa repository:
rem      tools\PUBBLICA_ORACOLO.bat
rem      tools\PUBBLICA_ORACOLO.bat "C:\percorso\ORACOLO_SOVRANO_WEB_AUTORIZZATO"
rem
rem  Tre differenze dal .bat del pacchetto, e ognuna e' un difetto trovato
rem  leggendolo:
rem
rem  1. CALL davanti a npm e vercel. Su Windows sono file .cmd: un .bat che
rem     ne chiama un altro senza CALL non torna mai indietro. Il .bat del
rem     pacchetto finisce li' — dopo il login sembra che non sia successo
rem     niente, e i passi 4/4 non vengono mai eseguiti.
rem  2. Il clone viene AGGIORNATO. Il .bat del pacchetto clona solo se la
rem     cartella non c'e': se c'e' ed e' vecchia, prepara una release dal
rem     sito di un'altra settimana senza dirlo.
rem  3. Passa da tools\prepare_release.py di questa repository, che applica
rem     ANCHE la consegna del 04/09 (barra di navigazione, quattro pagine
rem     che sbordavano su telefono, costo a terra). Il .bat del pacchetto
rem     pubblica il solo Oracolo, e quel lavoro resterebbe fuori.
rem
rem  Questo file si ferma all'ANTEPRIMA. La produzione la digiti tu.
rem ===================================================================

cd /d "%~dp0.."

set "PACCHETTO=%~1"
if "%PACCHETTO%"=="" set "PACCHETTO=..\ORACOLO_SOVRANO_WEB_AUTORIZZATO"
set "SITO=..\Claudio-sito"
set "RELEASE=..\Claudio-release"

echo.
echo === Oracolo del Sovrano: preparazione e ANTEPRIMA ===
echo  pacchetto: %PACCHETTO%
echo.

if not exist "%PACCHETTO%\MANIFEST_SHA256.json" (
  echo FERMO: in %PACCHETTO% non c'e' MANIFEST_SHA256.json.
  echo Scompatta il pacchetto ORACOLO_SOVRANO_WEB_AUTORIZZATO accanto a questa
  echo repository, oppure passa il suo percorso come primo argomento.
  goto :fine
)

echo [1/4] Python
py --version || goto :niente_python

echo.
echo [2/4] Il sito: clono o aggiorno %SITO%
if exist "%SITO%\.git" (
  git -C "%SITO%" pull --ff-only || goto :clone_vecchio
) else (
  git clone https://github.com/claudioterzi/Claudio.git "%SITO%" || goto :fine
)

echo.
echo [3/4] Preparazione della copia privata
py tools\prepare_release.py "%SITO%" "%RELEASE%" --forza --oracolo "%PACCHETTO%"
if errorlevel 1 goto :fine

echo.
echo [4/4] Vercel
where vercel >nul 2>nul || goto :manca_vercel
call vercel whoami >nul 2>nul || goto :manca_login
call py "%PACCHETTO%\tools\publish.py" "%RELEASE%"
if errorlevel 1 goto :fine

echo.
echo ===================================================================
echo  ANTEPRIMA PUBBLICATA. Il sito vero non e' cambiato.
echo  Aprila e guarda: /alpha, /tarot, una lettura intera, la Soglia,
echo  e la barra in alto dal telefono.
echo.
echo  Se va bene, la produzione e' questa riga, e la digiti tu:
echo    py "%PACCHETTO%\tools\publish.py" "%RELEASE%" --production --preview-tested
echo ===================================================================
goto :fine

:niente_python
echo FERMO: Python non trovato. Serve Python 3.10 o successivo.
goto :fine

:clone_vecchio
echo FERMO: %SITO% esiste ma non si aggiorna da solo (modifiche locali, o un
echo altro ramo). Guardalo: una release preparata da un clone vecchio pubblica
echo il sito di un'altra settimana senza dirtelo.
goto :fine

:manca_vercel
echo FERMO: vercel non e' installato. Due comandi, una volta sola:
echo    npm.cmd install --global vercel
echo    vercel.cmd login
echo Non lo installo io: e' una modifica a tutto il computer, e la decidi tu.
goto :fine

:manca_login
echo FERMO: vercel non sa chi sei. Una volta sola:
echo    vercel.cmd login
goto :fine

:fine
echo.
pause
endlocal
