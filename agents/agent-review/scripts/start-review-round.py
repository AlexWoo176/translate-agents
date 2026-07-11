import os
import sys
import glob

def start_review(file_path):
    # ── T6: Validate input trước khi tạo file ─────────────────────────────
    if not os.path.exists(file_path):
        print(f"❌ Không tìm thấy file: {file_path}")
        print("   Kiểm tra lại đường dẫn file HTML.")
        sys.exit(1)

    if '05-translated' not in file_path.replace('\\', '/'):
        print(f"❌ File phải nằm trong thư mục '05-translated/'.")
        print(f"   Đường dẫn nhận được: {file_path}")
        print("   Ví dụ đúng: ../entrepreneurship/chapter-1/05-translated/1-introduction.html")
        sys.exit(1)

    filename = os.path.basename(file_path).replace('.html', '')
    review_dir = os.path.dirname(file_path).replace('05-translated', '06-reviews')
    os.makedirs(review_dir, exist_ok=True)
    
    existing_rounds = glob.glob(os.path.join(review_dir, f"{filename}-semantic-review-round-*.md"))
    next_round = len(existing_rounds) + 1
    
    new_review_file = os.path.join(review_dir, f"{filename}-semantic-review-round-{next_round}.md")
    
    if next_round == 1:
        content = f"# Báo cáo Nghiệm thu: {filename}.html (Round 1)\n\n| ID | Thẻ Gốc | Bản dịch hiện tại | Phản biện | Đề xuất sửa | Phản hồi Translate Agent | Trạng thái |\n|---|---|---|---|---|---|---|\n"
    else:
        # Read the previous round to copy unresolved issues
        prev_round_file = os.path.join(review_dir, f"{filename}-semantic-review-round-{next_round-1}.md")
        with open(prev_round_file, 'r', encoding='utf-8') as f:
            prev_content = f.read()
        content = f"# Báo cáo Nghiệm thu: {filename}.html (Round {next_round})\n\n*(Kế thừa từ Round {next_round-1} và thêm lỗi mới)*\n\n{prev_content}"

    with open(new_review_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Đã tạo file review mới: {new_review_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: python3 start-review-round.py <đường dẫn file HTML trong 05-translated/>")
    else:
        start_review(sys.argv[1])

