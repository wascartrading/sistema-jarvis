' Lanza el servidor web de DeepSeek Harness totalmente oculto (sin ventana, sin parpadeo).
' El 0 en Run oculta la ventana; False = no esperar a que termine.
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c dsh web >> ""%USERPROFILE%\.dsh\dsh_web.log"" 2>&1", 0, False