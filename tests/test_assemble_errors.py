'Test of QPU assembler'

from nose.tools import raises, assert_raises
from struct import pack
from copy import deepcopy

import videocore.assembler as A
from videocore.assembler import REGISTERS, AssembleError, assemble, qpu



#=================================== Register =================================

def test_register_names():
    for name in REGISTERS:
        reg = REGISTERS[name]
        assert(reg.name == name)
        assert(str(reg) == name)

def test_pack_unpack():
    REGISTERS['ra0'].pack('16a')  # no throw
    assert_raises(AssembleError, REGISTERS['rb0'].pack, '16a')
    REGISTERS['ra0'].unpack('16a')  # no throw
    REGISTERS['r4'].unpack('16a')   # no throw
    assert_raises(AssembleError, REGISTERS['rb0'].unpack, '16a')

#============================ Instruction encoding ============================

SAMPLE_ALU_INSN = A.AluInsn(
    sig=0, unpack=1, pm=1, pack=2, cond_add=3, cond_mul=4, sf=1, ws=1,
    waddr_add=53, waddr_mul=12, op_mul=4, op_add=2, raddr_a=33, raddr_b=53,
    add_a=4, add_b=7, mul_a=6, mul_b=2
    )

SAMPLE_BRANCH_INSN = A.BranchInsn(
    sig=0xf, cond_br=13, rel=1, reg=0, raddr_a=27, ws=1, waddr_add=53,
    waddr_mul=12, immediate=0x12345678
    )

SAMPLE_LOAD_INSN = A.LoadInsn(
    sig=0xe, unpack=1, pm=1, pack=2, cond_add=3, cond_mul=4, sf=1, ws=1,
    waddr_add=53, waddr_mul=12, immediate=0x12345678
    )

SAMPLE_SEMA_INSN = A.SemaInsn(
    sig=0xe, unpack=4, pm=1, pack=2, cond_add=3, cond_mul=4, sf=1, ws=1,
    waddr_add=53, waddr_mul=12, sa=1, semaphore=13
    )

def test_equality():
    assert SAMPLE_ALU_INSN == SAMPLE_ALU_INSN
    assert SAMPLE_ALU_INSN != SAMPLE_BRANCH_INSN

def test_bytes_conversion():
    for sample_insn in [SAMPLE_ALU_INSN, SAMPLE_BRANCH_INSN,
                        SAMPLE_LOAD_INSN, SAMPLE_SEMA_INSN]:
        insn = A.Insn.from_bytes(sample_insn.to_bytes())
        assert insn == sample_insn

def test_insn_repr():
    assert repr(SAMPLE_ALU_INSN) == (
            'AluInsn(sig=0x0L, unpack=0x1L, pm=0x1L, pack=0x2L, '
            'cond_add=0x3L, cond_mul=0x4L, sf=0x1L, ws=0x1L, waddr_add=0x35L, '
            'waddr_mul=0xcL, op_mul=0x4L, op_add=0x2L, raddr_a=0x21L, '
            'raddr_b=0x35L, add_a=0x4L, add_b=0x7L, mul_a=0x6L, mul_b=0x2L)'
            )

def test_ignore_dontcare():
    assert repr(SAMPLE_BRANCH_INSN) == (
            'BranchInsn(sig=0xfL, cond_br=0xdL, rel=0x1L, reg=0x0L, '
            'raddr_a=0x1bL, ws=0x1L, waddr_add=0x35L, waddr_mul=0xcL, '
            'immediate=0x12345678L)'
            )
    insn1 = deepcopy(SAMPLE_BRANCH_INSN)
    insn2 = deepcopy(SAMPLE_BRANCH_INSN)
    insn1.dontcare = 0x1
    insn2.dontcare = 0x2
    assert insn1 == insn2


#================================== Assemble ==================================

@qpu
def dest_reg_conflict(asm):
    iadd(ra0, r0, r1).fmul(ra1, r2, r3)

@qpu
def too_many_regA(asm):
    iadd(r0, ra0, ra1)

@qpu
def too_many_regB(asm):
    iadd(r0, rb0, rb1)

@qpu
def too_many_imm(asm):
    iadd(r0, 1, 2)

@qpu
def regB_imm_conflict(asm):
    iadd(r0, rb0, 1)

@qpu
def not_read_operand(asm):
    iadd(r0, r0, vpm_ld_addr)

@qpu
def too_many_regfile_operands(asm):
    iadd(r0, uniform, varying_read).fmul(r1, element_number, qpu_number)

def test_operand_conflict():
    assert_raises(AssembleError, assemble, dest_reg_conflict)
    assert_raises(AssembleError, assemble, too_many_regA)
    assert_raises(AssembleError, assemble, too_many_regB)
    assert_raises(AssembleError, assemble, too_many_imm)
    assert_raises(AssembleError, assemble, regB_imm_conflict)
    assert_raises(AssembleError, assemble, not_read_operand)
    assert_raises(AssembleError, assemble, too_many_regfile_operands)

@qpu
def signal_imm_conflict_1(asm):
    iadd(r0, r0, 1, sig='thread switch')

@qpu
def signal_imm_conflict_2(asm):
    fmul(r0, r0, 2.0, sig='thread switch')

@qpu
def signal_imm_conflict_3(asm):
    fmul(r0, r0, 2.0, rotate=1)

@qpu
def signal_signal_conflict(asm):
    iadd(r0, r0, r0, sig='thread switch').fmul(r0, r0, r0, sig='breakpoint')

def test_signal_conflict():
    assert_raises(AssembleError, assemble, signal_imm_conflict_1)
    assert_raises(AssembleError, assemble, signal_imm_conflict_2)
    assert_raises(AssembleError, assemble, signal_imm_conflict_3)
    assert_raises(AssembleError, assemble, signal_signal_conflict)

@qpu
def pack_conflict_1(asm):
    iadd(ra0.pack('16a'), r0, r1).fmul(ra1.pack('16a'), r2, r3)

@qpu
def pack_conflict_2(asm):
    iadd(ra0.pack('16a'), r0, r1).fmul(rb0, r2, r3, pack='rep 8')

@qpu
def unpack_conflict(asm):
    iadd(r0, ra0.unpack('16a'), r4.unpack('16a'))

@qpu
def pack_unpack_conflict_1(asm):
    iadd(ra0.pack('16a'), r4.unpack('16a'), r0)

@qpu
def pack_unpack_conflict_2(asm):
    fmul(r0, ra0.unpack('16a'), r0, pack='8a')

@qpu
def pack_unpack_not_conflict_1(asm):
    iadd(ra0.pack('16a'), ra1.unpack('16b'), r0)

@qpu
def pack_unpack_not_conflict_2(asm):
    fmul(r0, r4.unpack('16a'), r0, pack='rep 8')

def test_pack_unpack_conflict():
    assert_raises(AssembleError, assemble, pack_conflict_1)
    assert_raises(AssembleError, assemble, pack_conflict_2)
    assert_raises(AssembleError, assemble, unpack_conflict)
    assert_raises(AssembleError, assemble, pack_unpack_conflict_1)
    assert_raises(AssembleError, assemble, pack_unpack_conflict_2)
    assemble(pack_unpack_not_conflict_1)    # no throw
    assemble(pack_unpack_not_conflict_2)    # no throw

@qpu
def invalid_rotate_insn(asm):
    fmul(r0, ra0, r2, rotate=2)

@raises(AssembleError)
def test_invalid_rotate_insn():
    assemble(invalid_rotate_insn)

@qpu
def unsupported_immediate(asm):
    ldi(r0, "Hello")

@qpu
def too_many_immediate(asm):
    ldi(r0, [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

@qpu
def invalid_per_elmt_immediate_1(asm):
    ldi(r0, [1, 1, 1, 1, 1, 4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

@qpu
def invalid_per_elmt_immediate_2(asm):
    ldi(r0, [1, -1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

@qpu
def invalid_per_elmt_immediate_3(asm):
    ldi(r0, [1, -3, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

def test_invalid_immediate():
    assert_raises(AssembleError, assemble, unsupported_immediate)
    assert_raises(AssembleError, assemble, too_many_immediate)
    assert_raises(AssembleError, assemble, invalid_per_elmt_immediate_1)
    assert_raises(AssembleError, assemble, invalid_per_elmt_immediate_2)
    assert_raises(AssembleError, assemble, invalid_per_elmt_immediate_3)

@qpu
def invalid_branch_target(asm):
    jmp("hello")

@qpu
def invalid_branch_regfile(asm):
    jmp(reg=rb0)

@qpu
def packing_of_link_register(asm):
    jmp(link=ra0.pack('16a'))

@qpu
def duplicated_label(asm):
    L._1
    L._1

@qpu
def undefined_label(asm):
    jmp(L._1)

def test_assemble_branch_insn():
    assert_raises(AssembleError, assemble, invalid_branch_target)
    assert_raises(AssembleError, assemble, invalid_branch_regfile)
    assert_raises(AssembleError, assemble, packing_of_link_register)
    assert_raises(AssembleError, assemble, duplicated_label)
    assert_raises(AssembleError, assemble, undefined_label)

@qpu
def invalid_semaphore_insn(asm):
    sema_up(17)

def test_invalid_sema_insn():
    assert_raises(AssembleError, assemble, invalid_semaphore_insn)
