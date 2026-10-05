# 第二轮：提高人物辨识度（只动"人物身份"这一个模块）
# 三个变量逐个隔离：
#   r1 = v1 提示词（与上一轮完全相同）+ 新增的脸部特写参考  → 单独看"加脸特写"的效果
#   r2/r3 = v2 提示词（加了带几何锚点的身份项 + 身份漂移负向）+ 脸特写 → 版1 出两次看方差
#   r4 = v3 提示词（v2 + 图2 招牌的"单眼眨 + 得意微笑"表情）
$env:PYTHONIOENCODING = 'utf-8'
$RL  = 'style-distill/round_lib/run_round.py'
$CON = 'style-distill/round_arcade/input/C_pose_env_2x3.png'
$REF = 'style-distill/round_arcade/input/B_char_style.png'
$FAC = 'style-distill/round_arcade/input/D_face_closeup.png'
$P1  = 'style-distill/round_arcade/prompt_arcade_v1.txt'
$P2  = 'style-distill/round_arcade/prompt_arcade_v2.txt'
$P3  = 'style-distill/round_arcade/prompt_arcade_v3.txt'
$OUT = 'style-distill/round_arcade'

python -u $RL --content $CON --ref $REF --ref $FAC `
  --prompt $P1 --out "$OUT/out_v2_r1_v1prompt_faceref.png" `
  --prompt $P2 --out "$OUT/out_v2_r2_idanchor.png" `
  --prompt $P2 --out "$OUT/out_v2_r3_idanchor.png" `
  --prompt $P3 --out "$OUT/out_v2_r4_wink.png" `
  --size 1024x1536 --encode jpg --concurrency 1
