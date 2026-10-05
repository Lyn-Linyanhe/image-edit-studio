# 第一轮：动作/环境取图1、人物与风格取图2 —— 一次出 3 版择优（顺序跑，避免下载互抢带宽）
# 目的有二：① 验证中转站是否接受 JPEG 投喂；② 同提示词多版采样，看这版方向对不对
$env:PYTHONIOENCODING = 'utf-8'
$RL   = 'style-distill/round_lib/run_round.py'
$CON  = 'style-distill/round_arcade/input/C_pose_env_2x3.png'
$REF  = 'style-distill/round_arcade/input/B_char_style.png'
$P    = 'style-distill/round_arcade/prompt_arcade_v1.txt'
$OUT  = 'style-distill/round_arcade'

python -u $RL --content $CON --ref $REF `
  --prompt $P --out "$OUT/out_v1_r1.png" `
  --prompt $P --out "$OUT/out_v1_r2.png" `
  --prompt $P --out "$OUT/out_v1_r3.png" `
  --size 1024x1536 --encode jpg --concurrency 1
