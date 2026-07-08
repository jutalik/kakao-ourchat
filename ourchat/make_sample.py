#!/usr/bin/env python3
"""Generate a synthetic KakaoTalk-export CSV so the repo runs end-to-end with ZERO
real data. Deterministic (seeded). Same Date,User,Message shape as a real export."""
import csv, datetime, random, argparse
random.seed(42)
NAMES = ["빛나는 수달","코드짜는 곰","질문요정","밤샘개발자","링크수집가","조용한관찰자",
         "논쟁왕","드립장인","신입인사","프로덕트메이커","서버지기","디자인하는나무",
         "커피중독","모델러","프롬프트냥이","오픈소스러","취준생J","클라우드덕후"]
TOPICS = {
  "AI": ["요즘 클로드 코드 진짜 좋네요","gpt랑 비교하면 어때요?","로컬 모델 돌려보신 분?","토큰 값이 부담이네요 ㅠㅠ","임베딩 모델 추천 좀요","에이전트 오케스트레이션 재밌음"],
  "배포": ["도커 컴포즈로 올렸어요","caddy 리버스프록시 편하던데요","오라클 프리티어 쓰는 중","배포 자동화 어떻게 하세요?"],
  "잡담": ["다들 점심 뭐 드셨어요","ㅋㅋㅋㅋ 이건 못참지","주말에 뭐하세요","오늘 날씨 좋네요","커피 한 잔 하고 갑니다"],
  "질문": ["이거 혹시 어떻게 하나요?","에러 나는데 봐주실 분?","무슨 라이브러리 쓰세요?","이 방식이 맞나요?"],
  "홍보": ["사이드프로젝트 오픈했어요 https://example.com 구경오세요","베타 테스터 모집합니다","저희 서비스 피드백 부탁드려요"],
}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="sample_export.csv"); ap.add_argument("--n",type=int,default=4000)
    a=ap.parse_args()
    t=datetime.datetime(2026,1,5,9,0,0)
    with open(a.out,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.writer(f); w.writerow(["Date","User","Message"])
        for i in range(a.n):
            t += datetime.timedelta(seconds=random.randint(20,900))
            u=random.choice(NAMES); topic=random.choice(list(TOPICS)); m=random.choice(TOPICS[topic])
            if random.random()<0.06: m="사진"
            elif random.random()<0.03: m="이모티콘"
            w.writerow([t.strftime("%Y-%m-%d %H:%M:%S"),u,m])
    print("wrote",a.out,a.n,"rows")
if __name__=="__main__": main()
