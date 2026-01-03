整个playground分为两个大的section，一个是LLM section，一个是ACEStep section

1. LLM section
内部有三个sub section
    1. LLM模型加载section
    2. 输入section，包含 caption， lyric， meta， config， negative caption， negative lyrics，以及一个 generate 按钮 
    3. 结果section



2. ACEStep section
内部有几个 sub section
    1. ACEstep其它几个模型，包括DIT VAE 这些模型的加载
    2. 任务模型下拉菜单
        [generate, repaint, cover, lego, complete, extract]
       
        1. 所有的任务都有 caption(prompt) 和 lyrics的输入， 所有的任务都可以有 Reference audio的输入, 所有的任务都可以有 audio_code_string 的输入
        2. repaint, cover, lego, complete, extract 这几个任务还需要再输入一个 source audio 
        3. repaint 需要输入 repaint_start 和 repaint_end， 分别代表 在source audio的几秒到几秒处 重新生成
        4. cover 还可以输入 audio_cover_strength

    3. 逻辑条件输入模块
        meta条件：bpm, target_duration, key_scale, time_signature
        vocal language 条件
    5. 结果展示模块

