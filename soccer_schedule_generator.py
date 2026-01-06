#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ジュニア世代の8人制サッカー大会
スターティングメンバーと交代スケジュール生成スクリプト v3
GK経験者が全試合通算でFP時間を均等に確保できるよう改善
"""

import csv
import random
from typing import List, Dict, Tuple
import sys


class Player:
    """選手クラス"""
    def __init__(self, name: str):
        self.name = name
        self.fp_time = 0  # FPとしての出場時間（全試合合計）
        self.fp_time_per_match = {}  # 各試合でのFP出場時間
        self.gk_count = 0  # GKを務めた試合数
        self.target_fp_time = 0  # 目標FP出場時間（全試合）


def generate_random_names(count: int) -> List[str]:
    """ランダムな選手名を生成"""
    first_names = [
        'Alex', 'Ben', 'Chris', 'David', 'Emma', 'Felix', 'George', 'Hannah',
        'Ian', 'Jack', 'Kate', 'Leo', 'Mike', 'Nina', 'Oscar', 'Peter',
        'Quinn', 'Rose', 'Sam', 'Tom'
    ]
    random.shuffle(first_names)
    return first_names[:count]


def calculate_target_times(players: List[Player], num_matches: int, duration: int):
    """
    各選手の目標FP出場時間を計算
    - GK経験者は他の試合で多めに出場する必要がある
    """
    num_players = len(players)
    total_fp_time = num_matches * duration * 7  # 全試合の総FP時間
    
    # 基本的な目標時間（全員同じ）
    base_target = total_fp_time / num_players
    
    for p in players:
        # GKを1試合務めると、その試合でFP時間が0なので、
        # 他の試合で補う必要がある
        # 目標 = 基本目標 + (GK試合数 × 試合時間)
        p.target_fp_time = base_target


def calculate_fair_rotation(players: List[Player], match_num: int, duration: int, num_matches: int) -> Tuple[str, Dict[int, List[str]]]:
    """
    公平なローテーションを計算
    """
    num_players = len(players)
    num_fp_spots = 7
    
    # GKを選択（GK経験が少ない順）
    sorted_by_gk = sorted(players, 
                         key=lambda p: (p.gk_count, p.fp_time))
    gk_player = sorted_by_gk[0]
    
    # FP候補
    fp_candidates = [p for p in players if p.name != gk_player.name]
    
    # 各選手の試合ごとのFP出場時間を初期化
    for p in fp_candidates:
        if match_num not in p.fp_time_per_match:
            p.fp_time_per_match[match_num] = 0
    
    # 各選手の残り試合数と、まだ必要なFP時間を計算
    def get_priority(player):
        """優先度を計算（値が小さいほど優先度が高い）"""
        # この選手があと何試合FPとして出られるか
        remaining_matches = num_matches - match_num + 1
        
        # もしこの選手が今回GKなら、残り試合から1を引く
        if player.name == gk_player.name:
            remaining_matches -= 1
        
        # すでにGKを経験している場合、GK1試合につき試合時間の2倍を失ったとみなす
        # これによりGK経験者がより優先的に起用される
        gk_lost_time = player.gk_count * duration * 2.0
        
        # まだ必要なFP時間（目標 - 実績 + GKで失った時間）
        needed_time = player.target_fp_time - player.fp_time + gk_lost_time
        
        # 1試合あたりの必要時間
        if remaining_matches > 0:
            time_per_match = needed_time / remaining_matches
        else:
            time_per_match = needed_time
        
        # GK経験者の場合、必要時間をさらに強調（3倍にする）
        if player.gk_count > 0:
            time_per_match = time_per_match * 3.0
        
        # 優先度を返す：
        # 1. GK経験者かどうか（GK経験者を最優先）
        # 2. この試合での出場時間（少ない方が優先）
        # 3. 1試合あたりの必要時間（多い方が優先＝負の値が小さい）
        # 4. 全試合での出場時間（少ない方が優先）
        return (-player.gk_count, player.fp_time_per_match.get(match_num, 0), -time_per_match, player.fp_time)
    
    # 優先度順にソート
    fp_sorted = sorted(fp_candidates, key=get_priority)
    
    # スケジュールを作成
    schedule = {}
    current_on_field = [p.name for p in fp_sorted[:num_fp_spots]]
    schedule[0] = {
        'gk': gk_player.name,
        'fp': current_on_field.copy()
    }
    
    # 3分ごとにローテーション
    interval = 3
    current_time = interval
    player_last_on = {name: 0 for name in current_on_field}
    
    while current_time < duration:
        # 現在の出場時間を更新
        for name in current_on_field:
            idx = next(i for i, p in enumerate(fp_candidates) if p.name == name)
            fp_candidates[idx].fp_time_per_match[match_num] += interval
            fp_candidates[idx].fp_time += interval
        
        # 交代可能な選手
        can_sub_off = [name for name in current_on_field 
                      if current_time - player_last_on[name] >= interval]
        
        if can_sub_off:
            on_bench = [p.name for p in fp_candidates if p.name not in current_on_field]
            
            if on_bench:
                # 優先度で再ソート
                bench_sorted = sorted(on_bench,
                                     key=lambda name: get_priority(next(p for p in fp_candidates if p.name == name)))
                
                field_sorted = sorted(can_sub_off,
                                     key=lambda name: get_priority(next(p for p in fp_candidates if p.name == name)),
                                     reverse=True)
                
                # 交代人数を決定
                # ベンチに優先度が高い（まだ出場時間が足りない）選手がいる場合は多めに交代
                # ただし、GK経験者が既にピッチにいる場合は、その選手を下げないように配慮
                bench_priorities = [get_priority(next(p for p in fp_candidates if p.name == name))[1] 
                                  for name in bench_sorted[:min(5, len(bench_sorted))]]
                field_priorities = [get_priority(next(p for p in fp_candidates if p.name == name))[1] 
                                  for name in field_sorted[:min(5, len(field_sorted))]]
                
                # ピッチにGK経験者がいるかチェック
                gk_exp_on_field = [name for name in current_on_field
                                  if next(p.gk_count for p in fp_candidates if p.name == name) > 0]
                
                # ベンチにGK経験者がいるかチェック
                gk_exp_on_bench = [name for name in bench_sorted
                                  if next(p.gk_count for p in fp_candidates if p.name == name) > 0]
                
                if gk_exp_on_bench:
                    # GK経験者がベンチにいる場合は必ず入れる + 他にも交代
                    num_subs = min(len(field_sorted), len(bench_sorted), 4)
                elif bench_priorities and field_priorities:
                    avg_bench_need = sum(bench_priorities) / len(bench_priorities)
                    avg_field_need = sum(field_priorities) / len(field_priorities)
                    
                    if avg_bench_need < avg_field_need - 10:  # ベンチの方が必要度がかなり高い
                        num_subs = min(len(field_sorted), len(bench_sorted), 4)
                    elif avg_bench_need < avg_field_need - 5:
                        num_subs = min(len(field_sorted), len(bench_sorted), 3)
                    elif gk_exp_on_field:
                        # ピッチにGK経験者がいる場合は、交代を少なめに（その選手を守る）
                        num_subs = min(len(field_sorted), len(bench_sorted), 2)
                    else:
                        num_subs = min(len(field_sorted), len(bench_sorted), 3)
                else:
                    num_subs = min(len(field_sorted), len(bench_sorted), 2)
                
                # 交代実行
                if num_subs > 0:
                    subs = []
                    for i in range(num_subs):
                        off_player = field_sorted[i]
                        on_player = bench_sorted[i]
                        subs.append((off_player, on_player))
                        current_on_field.remove(off_player)
                        current_on_field.append(on_player)
                        player_last_on[on_player] = current_time
                    
                    schedule[current_time] = {'subs': subs}
        
        current_time += interval
    
    # 最後の区間の時間を加算
    remaining = duration - (current_time - interval)
    for name in current_on_field:
        idx = next(i for i, p in enumerate(fp_candidates) if p.name == name)
        fp_candidates[idx].fp_time_per_match[match_num] += remaining
        fp_candidates[idx].fp_time += remaining
    
    # GKのカウント
    gk_player.gk_count += 1
    gk_player.fp_time_per_match[match_num] = 0
    
    return gk_player.name, schedule


def write_csv(players: List[Player], all_schedules: List[Tuple[int, str, Dict]], output_file: str, duration: int):
    """CSVファイルに出力"""
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        for match_num, gk_name, schedule in all_schedules:
            writer.writerow([f'試合{match_num}'])
            header = ['時間(分)'] + [p.name for p in players]
            writer.writerow(header)
            
            # 0分時点
            row = ['0分']
            for p in players:
                if p.name == gk_name:
                    row.append('SM(GK)')
                elif p.name in schedule[0]['fp']:
                    row.append('SM')
                else:
                    row.append('RM')
            writer.writerow(row)
            
            # 交代タイミング
            current_status = {}
            for p in players:
                if p.name == gk_name:
                    current_status[p.name] = 'GK'
                elif p.name in schedule[0]['fp']:
                    current_status[p.name] = 'ON'
                else:
                    current_status[p.name] = 'OFF'
            
            for time in sorted([t for t in schedule.keys() if t > 0]):
                if 'subs' in schedule[time]:
                    row = [f'{time}分']
                    subs = schedule[time]['subs']
                    sub_dict = {off: 'OUT' for off, on in subs}
                    sub_dict.update({on: 'IN' for off, on in subs})
                    
                    for off, on in subs:
                        current_status[off] = 'OFF'
                        current_status[on] = 'ON'
                    
                    for p in players:
                        if p.name in sub_dict:
                            row.append(sub_dict[p.name])
                        else:
                            row.append('')
                    
                    writer.writerow(row)
            
            row = [f'{duration}分'] + ['' for _ in players]
            writer.writerow(row)
            writer.writerow([])


def print_statistics(players: List[Player], num_matches: int):
    """統計情報を表示"""
    print("\n=== 統計情報 ===")
    
    header = f"{'選手名':<15}"
    for i in range(1, num_matches + 1):
        header += f" {'試合' + str(i):<10}"
    header += f" {'合計':<10} {'GK出場':<10}"
    print(header)
    print("-" * (15 + num_matches * 11 + 20))
    
    for p in sorted(players, key=lambda x: x.name):
        row = f"{p.name:<15}"
        for i in range(1, num_matches + 1):
            fp_time = p.fp_time_per_match.get(i, 0)
            row += f" {fp_time:<10}分"
        row += f" {p.fp_time:<10}分 {p.gk_count:<10}試合"
        print(row)
    
    print()
    for i in range(1, num_matches + 1):
        match_times = [p.fp_time_per_match.get(i, 0) for p in players]
        match_avg = sum(match_times) / len(match_times)
        match_min = min(match_times)
        match_max = max(match_times)
        print(f"試合{i}: 平均{match_avg:.1f}分 (最小{match_min}分, 最大{match_max}分)")
    
    avg_fp_time = sum(p.fp_time for p in players) / len(players)
    min_fp = min(p.fp_time for p in players)
    max_fp = max(p.fp_time for p in players)
    print(f"\nFP出場時間（全試合合計）: 平均{avg_fp_time:.1f}分 (最小{min_fp}分, 最大{max_fp}分)")
    print(f"GK経験者数: {sum(1 for p in players if p.gk_count > 0)}人 / {len(players)}人")


def main():
    print("=" * 60)
    print("ジュニア世代8人制サッカー 試合スケジュール生成 v3")
    print("=" * 60)
    
    try:
        num_matches = int(input("\n試合数を入力してください: "))
        if num_matches < 1:
            print("エラー: 試合数は1以上である必要があります。")
            sys.exit(1)
        
        match_duration = int(input("1試合の時間（分）を入力してください: "))
        if match_duration < 3:
            print("エラー: 試合時間は3分以上である必要があります。")
            sys.exit(1)
        
        # メンバー名を入力
        print("\nメンバー名をカンマ区切りで入力してください。")
        print("例: 太郎,次郎,三郎,四郎,五郎,六郎,七郎,八郎")
        player_names_input = input("メンバー名: ")
        
        # カンマで分割して空白を削除
        player_names = [name.strip() for name in player_names_input.split(',') if name.strip()]
        
        num_players = len(player_names)
        
        if num_players < 8:
            print("エラー: メンバー数は8人以上である必要があります。")
            sys.exit(1)
        if num_players > 18:
            print("エラー: メンバー数は18人以下である必要があります。")
            sys.exit(1)
        
        # 名前の重複チェック
        if len(player_names) != len(set(player_names)):
            print("エラー: 同じ名前のメンバーが含まれています。")
            sys.exit(1)
        
    except ValueError:
        print("エラー: 数値を入力してください。")
        sys.exit(1)
    
    print(f"\n生成中...（メンバー数: {num_players}人）")
    
    # 選手を生成
    players = [Player(name) for name in player_names]
    
    # 目標FP時間を計算
    calculate_target_times(players, num_matches, match_duration)
    
    # 各試合のスケジュールを生成
    all_schedules = []
    for match_num in range(1, num_matches + 1):
        gk_name, schedule = calculate_fair_rotation(players, match_num, match_duration, num_matches)
        all_schedules.append((match_num, gk_name, schedule))
    
    # CSV出力
    output_file = 'soccer_schedule.csv'
    write_csv(players, all_schedules, output_file, match_duration)
    
    print(f"\n✓ スケジュールを '{output_file}' に出力しました。")
    
    # 統計情報表示
    print_statistics(players, num_matches)


if __name__ == "__main__":
    main()
