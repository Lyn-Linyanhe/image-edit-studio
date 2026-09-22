# R5 实验矩阵：给"正向蒙版是否有救"定性（3 次调用，顺序跑——并行下载会互抢带宽）
# 三个杠杆各排除一个机制假设：
#   a) --pad pad      构图归一化（crop 会裁掉 33% 宽度、改变模型看到的画面）
#   b) 可改面积 25%   小区域可能低于模型的有效编辑尺度（此前全是 1.25%–2.9%）
#   c) --mask-primary 抽掉"照抄干净原图把它恢复"的路径（顺带体积砍半）
$env:PYTHONIOENCODING = 'utf-8'
$RL  = 'style-distill/round_lib/run_round.py'
$IN  = 'style-distill/round_snow/input/C_snow_169.png'
$P   = 'style-distill/round_snow/lab/prompt_masktest4.txt'
$W   = 'style-distill/round_snow/work'
$L   = 'style-distill/round_snow/lab'

Write-Host '===== R5a: --pad pad ====='
python -u $RL --content $IN --prompt $P --out "$L/out_r5a_pad.png" --size 1024x1024 --mask "$W/mask_hair.png" --pad pad

Write-Host '===== R5b: 可改面积 25% ====='
python -u $RL --content $IN --prompt $P --out "$L/out_r5b_big.png" --size 1024x1024 --mask "$W/mask_big.png"

Write-Host '===== R5c: 只发涂红图（不发干净原图）====='
python -u $RL --content $IN --prompt $P --out "$L/out_r5c_primary.png" --size 1024x1024 --mask "$W/mask_hair.png" --mask-primary

Write-Host '===== R5 三次调用结束 ====='
