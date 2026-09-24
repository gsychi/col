
// Research-only profile of raw recursive states, using the production interaction graph.
pub fn research_fragment_score(n:usize,p1:u64,p2:u64)->u64 {
    let mut remaining=p1|p2;
    let mut score=0u64;
    while remaining!=0 {
        let size=take_component_3xn(n,p1,p2,&mut remaining).count_ones();
        if size>10 {score=score.saturating_add(1u64<<size);}
    }
    score
}

// Exact one-sided monotonic bounds, NOT unrestricted deletion of a separator.
// A win after restricting the actor's moves implies an original win.
// A loss after restricting the opponent's moves implies an original loss.
pub fn research_separator_bound(evaluator:&mut EndgameEvaluator,n:usize,p1:u64,p2:u64,turn:u8)->Option<bool> {
    for col in 0..n {
        let cut=(1u64<<col)|(1u64<<(n+col))|(1u64<<(2*n+col));
        for restricted in [turn,1-turn] {
            let (a,b)=if restricted==0 {(p1&!cut,p2)} else {(p1,p2&!cut)};
            if (a,b)==(p1,p2) {continue;}
            let mut remaining=a|b;
            let mut eligible=true;
            while remaining!=0 {
                if take_component_3xn(n,a,b,&mut remaining).count_ones()>evaluator.max_component_size {
                    eligible=false;break;
                }
            }
            if !eligible {continue;}
            let mut total=Value::zero();
            remaining=a|b;
            while remaining!=0 {
                let component=take_component_3xn(n,a,b,&mut remaining);
                let (shape,la,lb)=evaluator.local_shape_and_masks(n,a&component,b&component);
                total=total.add(evaluator.component_value_local(&shape,la,lb));
            }
            if turn!=0 {total=total.neg();}
            let wins=first_player_wins(total);
            if wins==(restricted==turn) {return Some(wins);}
        }
    }
    None
}

#[cfg(test)]
mod research_tests {
    use super::*;
    #[test]
    fn separator_bounds_agree_on_all_3x2_shadow_states() {
        let mut bounds=EndgameEvaluator::new(2,None);
        let mut exact=EndgameEvaluator::new(6,None);
        let mut hits=0;
        for a in 0..64 {for b in 0..64 {for turn in 0..2 {
            if let Some(wins)=research_separator_bound(&mut bounds,2,a,b,turn) {
                let (shape,la,lb)=exact.local_shape_and_masks(2,a,b);
                let mut value=exact.position_value_local(&shape,la,lb);
                if turn!=0 {value=value.neg();}
                assert_eq!(wins,first_player_wins(value),"a={a} b={b} turn={turn}");
                hits+=1;
            }
        }}}
        assert!(hits>100);
    }
}
pub fn research_pair(evaluator:&mut EndgameEvaluator,n:usize,p1:u64,p2:u64,turn:u8)->Option<String> {
    let mut remaining=p1|p2;
    let mut components=Vec::new();
    while remaining!=0 {components.push(take_component_3xn(n,p1,p2,&mut remaining));}
    if components.len()!=2 {return None;}
    components.sort_by_key(|c|std::cmp::Reverse(c.count_ones()));
    let large=components[0]; let small=components[1];
    let (actor,opponent)=if turn==0 {(p1,p2)} else {(p2,p1)};
    let core=component_signature(n,large,actor,opponent,false);
    let tiny=component_signature(n,small,actor,opponent,false);
    let charge=if small.count_ones()<=10 {
        let (shape,a,b)=evaluator.local_shape_and_masks(n,actor&small,opponent&small);
        format_value(evaluator.component_value_local(&shape,a,b))
    } else {"oversized".into()};
    // Minimum column deletion giving two residual regions of >=4 cells each.
    // This is separator prevalence, never an assertion that boundary masks suffice.
    let mut separator=4u32;
    for col in 0..n {
        let cut=large & ((1u64<<col)|(1u64<<(n+col))|(1u64<<(2*n+col)));
        if cut==0 {continue;}
        let mut rest=large & !cut;
        let mut sizes=Vec::new();
        while rest!=0 {sizes.push(take_component_3xn(n,actor & !cut,opponent & !cut,&mut rest).count_ones());}
        sizes.sort_unstable_by(|a,b|b.cmp(a));
        if sizes.len()>=2 && sizes[1]>=4 {separator=separator.min(cut.count_ones());}
    }
    Some(format!("2\t{}\t{}\t{:?}\t{:?}\t{}\t{}",large.count_ones(),small.count_ones(),core,tiny,charge,separator))
}
