set projectRoot to "/Users/seqi/projects/Openclaw-learn-helper"
set shellCommand to "cd " & quoted form of projectRoot & " && study-companion/scripts/run_snap_question.sh"

try
	do shell script "/bin/zsh -lc " & quoted form of shellCommand
on error errMsg number errNum
	display dialog "OpenClaw 截图识题启动失败：" & return & errMsg buttons {"OK"} default button "OK"
	error number errNum
end try
