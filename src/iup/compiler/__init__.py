from .pass_manager import *
from .compiler_register_allocator import *
from .compiler import *

ALL_PASSES_LIST: List[Pass] = [
    ShrinkPass(),
    RCOPass(),
    ExplicateControlPass(),
    SelectInstrPass(),
    AllocateRegPass(),
    AssignHomePass(),
    PatchInsPass(),
    PreConPass(),

    UncoverLivePass(),
    BuildInterferencePass()
]

ALL_PASSES: Dict[PassName, Pass] = {p.name: p for p in ALL_PASSES_LIST}


LvarTransforms: List[TransformPass] = [
    RCOPass(),
    SelectInstrPass(),
    AllocateRegPass(),
    PatchInsPass(),
    PreConPass()
]
LvarAnalyses: List[AnalysisPass] = [
    UncoverLivePass(),
    BuildInterferencePass()
]
LvarManager = PassManager(LvarTransforms, LvarAnalyses)


LifTransforms: List[TransformPass] = [
    ShrinkPass(),
    RCOPass(),
    ExplicateControlPass(),
    SelectInstrPass(),
    AllocateRegPass(),
    PatchInsPass(),
    PreConPass()
]
LifAnalyses: List[AnalysisPass] = [
    UncoverLivePass(),
    BuildInterferencePass()
]
LifManager = PassManager(LifTransforms, LifAnalyses, 'Lif')


