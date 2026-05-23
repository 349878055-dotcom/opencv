参考片目录（东方不败等电影镜头）

【方式 A】直接告诉我 YouTube 链接 + 起止时间，或在项目根执行：

  ./scripts/s01_从YouTube截取参考片.sh "https://www.youtube.com/watch?v=XXXX" "1:23" "1:28"
  ./scripts/s01_从YouTube截取参考片.sh "URL" "1:23" "1:28" --infer   # 截完自动反推

时间写法：1:23、01:02:03、或纯秒数 83.5。建议片段 5～8 秒、脸部特写。

【方式 B】自己截好的 mp4 放到本目录，命名为 参考片.mp4

2. 反推（若未加 --infer）：
   ./scripts/s01_从参考片反推.sh

3. 产出（在 ../指令/ 下）：
   03_逐帧反推.json      — 150 帧 × 12 通道稠密（均来自片子眼眉区）
   02_候选_从参考片.json — 12 通道收缩后的稀疏候选

4. 对照原片审定全部 12 轨后：
   ./scripts/s01_采纳候选指令.sh
   ./scripts/s01_主验收示意图.sh

   ECURSOR_INFER_FLIP_X=1 ./scripts/s01_从参考片反推.sh

要求：30fps、约 5 秒（150 帧）为佳；其它长度会强制抽 150 帧。
