# LinkedIn post

**Image:** `docs/assets/linkedin_poster.png` (portrait 4:5, 2160 x 2700, the format that fills the most of a phone
screen in the feed), rebuilt from `results/results.json` and the F1 render by `scripts/make_linkedin_poster.py`
(`make poster`; it needs `figures/F1_tree_of_open_models_5000.png` from `make figures`, or falls back to the paper's
smaller copy of the figure).

**Alt text for the image:** Poster titled "The Tree of Open Models". A large radial diagram on a dark background
shows 965,292 Hugging Face models that declare a parent or have a child, joined by 952,646 lineage links: angle is
lineage, radius is creation date from 2022 at the centre to November 2026 at the rim, and colour is the model family,
with Qwen, Llama, Mistral, Gemma, the BERT family and FLUX labelled around the rim. Below the tree, five headline
numbers: 74.8% of connected models descend from the top 1% of base models; merges join relatives 18 times more often
than chance; the median wait for the first fine-tune of a major base is 2.8 days, down from 35.1 in 2023; the top 1%
of derivatives receive 95.9% of derivative downloads; 18.7% of lineage links change task group.

Every number below is in the paper and on the poster. Post the links as the first comment.

---

## Post (English, about 2,600 characters)

What does the family tree of open AI models look like?

Hugging Face now hosts 3.2 million public models, and 28.6% of them declare a parent: they are fine-tunes, adapters, quantisations or merges of other models. I collected every one of those declarations into a single lineage graph, 965,292 models joined by 952,646 links, and read it the way a biologist reads a phylogeny.

The image below is the whole tree. Angle is lineage (each base's offspring sweep around it in birth order), radius is creation date, from early 2022 at the centre to November 2026 at the rim, and colour is the model family.

Five findings:

1. A few bases carry the ecosystem.
The top 1% of root models (458 of them) hold 74.8% of all connected models, and 95.1% of derivatives never have offspring of their own.

2. Merging favours relatives.
39.0% of merged models combine parents that share a declared ancestor, against 2.1% when parents are re-paired at random: 18 times more often than chance. The deepest chain is 142 merges long.

3. Derivatives arrive in days.
For heavily reused bases, the median wait for the first fine-tune fell from 35.1 days (bases released in late 2023) to 2.8 days (early 2026). Quantisations arrive just as fast.

4. Attention is even more skewed than reproduction.
The top 1% of uploaders produce 52.5% of all derivatives, and the top 1% of derivatives receive 95.9% of their downloads. 12.4% of derivatives were not downloaded once in the last 30 days.

5. Speciation follows architecture.
18.7% of parent-to-child links change task. The busiest route is fill-mask encoders becoming text classifiers (35,171 links); generative lineages almost never change task (4.8% for text generation).

Everything is open: a 19-page working draft, a pipeline that rebuilds every number and figure in one command, all research data on Hugging Face (including the pinned snapshot, so the results reproduce exactly), and a DOI on Zenodo. Links in the first comment.

Caveats up front: lineage is declared, not observed, so every count is a lower bound; creation time is not release time; and the license-drift analysis I originally planned is not in this draft, because the snapshot carries no per-model license tags.

The lineage data are the Open Model Family Tree by h9-tec (CC BY 4.0), built from the hub-stats dump of Hub metadata.

If you build, host or audit open models, I would value your critique. What would you want a model's family tree to tell you?

Personal research; views are my own.

#HuggingFace #OpenSourceAI #MachineLearning #DataVisualization #MLOps

---

## First comment (links)

Paper (read online): https://thanatchon36.github.io/open-model-phylogeny/paper/
Paper (PDF): https://github.com/thanatchon36/open-model-phylogeny/raw/main/paper/paper.pdf
Code: https://github.com/thanatchon36/open-model-phylogeny
Data: https://huggingface.co/datasets/thanatchon36/open-model-phylogeny
DOI: https://doi.org/10.5281/zenodo.24029159

---

## Post (Thai)

แผนภูมิวงศ์วานของโมเดล AI แบบเปิดหน้าตาเป็นอย่างไร?

ตอนนี้ Hugging Face มีโมเดลสาธารณะ 3.2 ล้านตัว และ 28.6% ในจำนวนนั้นประกาศว่าตัวเองมีพ่อแม่ คือเป็น fine-tune, adapter, quantisation หรือ merge ของโมเดลอื่น ผมรวบรวมการประกาศทั้งหมดนั้นมาเป็นกราฟวงศ์วานเดียว มีโมเดล 965,292 ตัว เชื่อมกันด้วยเส้น 952,646 เส้น แล้วอ่านมันแบบที่นักชีววิทยาอ่านแผนภูมิวิวัฒนาการ

ภาพด้านล่างคือต้นไม้ทั้งต้น มุมคือสายเลือด (ลูกหลานของแต่ละ base กวาดรอบตัวมันตามลำดับการเกิด) รัศมีคือวันที่สร้าง จากต้นปี 2022 ตรงกลางถึงพฤศจิกายน 2026 ที่ขอบ และสีคือตระกูลของโมเดล

ห้าข้อค้นพบ

1. base ไม่กี่ตัวแบกทั้งระบบนิเวศ
root model 1% แรก (458 ตัว) ครองโมเดลที่เชื่อมโยงกันทั้งหมด 74.8% และ 95.1% ของโมเดลลูกไม่เคยมีลูกหลานของตัวเองเลย

2. การ merge ชอบจับคู่ญาติ
39.0% ของโมเดลที่ merge ใช้พ่อแม่ที่มีบรรพบุรุษร่วมกัน เทียบกับ 2.1% เมื่อจับคู่พ่อแม่แบบสุ่ม คือบ่อยกว่าโอกาสสุ่ม 18 เท่า สายที่ลึกที่สุดซ้อนกัน 142 ชั้น

3. โมเดลลูกเกิดภายในไม่กี่วัน
สำหรับ base ที่ถูกนำไปใช้ต่อมาก เวลามัธยฐานกว่าจะมี fine-tune ตัวแรกลดจาก 35.1 วัน (base ที่ปล่อยปลายปี 2023) เหลือ 2.8 วัน (ต้นปี 2026) ส่วน quantisation ก็มาเร็วพอกัน

4. ความสนใจกระจุกตัวยิ่งกว่าการแพร่พันธุ์
ผู้อัปโหลด 1% แรกผลิตโมเดลลูก 52.5% ของทั้งหมด และโมเดลลูก 1% แรกได้ยอดดาวน์โหลดไป 95.9% ขณะที่โมเดลลูก 12.4% ไม่ถูกดาวน์โหลดเลยใน 30 วันล่าสุด

5. การเปลี่ยนงานขึ้นกับสถาปัตยกรรม
18.7% ของเส้นพ่อแม่ไปลูกเปลี่ยนประเภทงาน เส้นทางที่พบบ่อยที่สุดคือ encoder แบบ fill-mask กลายเป็น text classifier (35,171 เส้น) ส่วนสาย generative แทบไม่เปลี่ยนงานเลย (4.8% สำหรับ text generation)

ทุกอย่างเปิดหมด: working draft 19 หน้า pipeline ที่สร้างทุกตัวเลขและทุกภาพใหม่ได้ด้วยคำสั่งเดียว ข้อมูลวิจัยทั้งหมดบน Hugging Face (รวม snapshot ที่ตรึงไว้ จึงทำซ้ำได้ตรงทุกค่า) และ DOI บน Zenodo ลิงก์อยู่ในคอมเมนต์แรกครับ

ข้อควรระวัง: สายเลือดมาจากการประกาศ ไม่ใช่การสังเกต ทุกตัวเลขจึงเป็นค่าขั้นต่ำ วันที่สร้างไม่ใช่วันที่ปล่อย และการวิเคราะห์ license drift ที่วางแผนไว้แต่แรกยังไม่อยู่ในร่างนี้ เพราะ snapshot ไม่มี license tag รายโมเดล

ข้อมูลสายเลือดมาจาก Open Model Family Tree โดย h9-tec (CC BY 4.0) ซึ่งสร้างจาก dump ของ metadata บน Hub ใน hub-stats

ใครสร้าง โฮสต์ หรือตรวจสอบโมเดลแบบเปิด ยินดีรับคำวิจารณ์ครับ คุณอยากให้แผนภูมิวงศ์วานของโมเดลบอกอะไรคุณบ้าง?

งานวิจัยส่วนตัว ความเห็นเป็นของผมเอง

#HuggingFace #OpenSourceAI #MachineLearning #DataVisualization #MLOps

---

## Short version (English)

What does the family tree of open AI models look like?

I mapped all 965,292 Hugging Face models that declare a parent or have a child and read the graph as a phylogeny.

• The top 1% of base models hold 74.8% of all connected models.
• Merges join relatives 18 times more often than chance.
• The first fine-tune of a major base now arrives in a median 2.8 days, down from 35.1 in 2023.
• The top 1% of derivatives receive 95.9% of derivative downloads.
• 18.7% of lineage links change task, mostly encoders becoming classifiers.

Paper, code, data and DOI in the first comment.

#HuggingFace #OpenSourceAI #MachineLearning
