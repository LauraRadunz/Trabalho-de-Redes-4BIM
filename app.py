"""
Calculadora de sub-redes IPv4 (TINF - Trabalho T4)
Interface web feita com Streamlit.

Todos os cálculos são feitos com operações de bits (AND, OR, NOT, shifts).
Nenhuma biblioteca de rede é utilizada (nada de ipaddress).

Ideia central: um endereço IPv4 tem 32 bits, então podemos guardá-lo como
um único número inteiro. Ex.: 192.168.1.10 vira um número de 32 bits, e
aí as contas ficam simples:
    rede      = ip AND mascara
    broadcast = rede OR (NOT mascara)
"""

import streamlit as st

TODOS_OS_BITS = 0xFFFFFFFF  # 32 bits todos em 1


# ---------------------------------------------------------------------------
# Conversões
# ---------------------------------------------------------------------------

def ip_para_inteiro(texto):
    """Converte '192.168.1.10' em um inteiro de 32 bits.
    Levanta ValueError se o formato for inválido."""
    partes = texto.strip().split(".")
    if len(partes) != 4:
        raise ValueError(f"Endereço inválido '{texto}': precisa ter 4 octetos (ex.: 192.168.1.10).")

    numero = 0
    for parte in partes:
        if not parte.isdigit():
            raise ValueError(f"Endereço inválido '{texto}': '{parte}' não é um número.")
        octeto = int(parte)
        if octeto > 255:
            raise ValueError(f"Endereço inválido '{texto}': octeto {octeto} fora do intervalo de 0 a 255.")
        numero = (numero << 8) | octeto
    return numero


def inteiro_para_ip(numero):
    """Converte um inteiro de 32 bits de volta para '192.168.1.10'."""
    octetos = []
    for deslocamento in (24, 16, 8, 0):
        # desloca o octeto desejado para o final e pega só os 8 bits de baixo
        octetos.append(str((numero >> deslocamento) & 0xFF))
    return ".".join(octetos)


def inteiro_para_binario(numero):
    """Converte para binário separado por pontos: 11000000.10101000.00000001.00001010"""
    octetos = []
    for deslocamento in (24, 16, 8, 0):
        octeto = (numero >> deslocamento) & 0xFF
        octetos.append(format(octeto, "08b"))  # 8 dígitos, completando com zeros à esquerda
    return ".".join(octetos)


# ---------------------------------------------------------------------------
# Máscara
# ---------------------------------------------------------------------------

def prefixo_para_mascara(prefixo):
    """Prefixo /20 -> 20 bits 1 seguidos de 12 bits 0.
    Ex.: /20 = 11111111.11111111.11110000.00000000"""
    if prefixo == 0:
        return 0
    # (TODOS_OS_BITS << (32 - prefixo)) liga os bits e joga zeros à direita;
    # o AND corta o que passou de 32 bits
    return (TODOS_OS_BITS << (32 - prefixo)) & TODOS_OS_BITS


def mascara_para_prefixo(mascara):
    """Conta quantos bits 1 a máscara tem (isso é o prefixo)."""
    prefixo = 0
    for posicao in range(32):
        if (mascara >> posicao) & 1:
            prefixo += 1
    return prefixo


def mascara_e_valida(mascara):
    """Uma máscara válida é 1s seguidos de 0s (111...1000...0).
    Truque: invertendo os bits, sobra 000...0111...1. Somando 1 a isso,
    o número vira uma potência de 2 (100...0), e um AND entre os dois dá zero.
    Se tivesse um 1 'sozinho' no meio, o AND não daria zero."""
    invertida = ~mascara & TODOS_OS_BITS
    return (invertida & (invertida + 1)) == 0


def ler_mascara(texto):
    """Aceita '/20', '20' ou '255.255.240.0'. Devolve (mascara_inteiro, prefixo)."""
    texto = texto.strip()

    # Notação de prefixo
    if texto.startswith("/") or texto.isdigit():
        numero = texto.lstrip("/")
        if not numero.isdigit():
            raise ValueError(f"Prefixo inválido '{texto}'.")
        prefixo = int(numero)
        if prefixo > 32:
            raise ValueError(f"Prefixo /{prefixo} fora do intervalo de 0 a 32.")
        if prefixo < 0:
                    raise ValueError(f"Prefixo /{prefixo} fora do intervalo de 0 a 32.")
        return prefixo_para_mascara(prefixo), prefixo

    # Notação decimal pontuada
    mascara = ip_para_inteiro(texto)
    if not mascara_e_valida(mascara):
        raise ValueError(f"Máscara inválida '{texto}': os bits 1 precisam ser contíguos.")
    return mascara, mascara_para_prefixo(mascara)


# ---------------------------------------------------------------------------
# Cálculo principal
# ---------------------------------------------------------------------------

def calcular(ip, mascara):
    """Faz todos os cálculos e devolve um dicionário com os resultados."""
    ip = ip_para_inteiro(ip)
    mascara, prefixo = ler_mascara(mascara)

    rede = ip & mascara                           # zera os bits de host
    broadcast = rede | (~mascara & TODOS_OS_BITS)  # liga todos os bits de host
    bits_de_host = 32 - prefixo

    resultado = {
        "ip_binario": inteiro_para_binario(ip),
        "prefixo": f"/{prefixo}",
        "mascara_decimal": inteiro_para_ip(mascara),
        "mascara_binario": inteiro_para_binario(mascara),
    }

    if prefixo == 32:
        # Host único: não existe rede nem broadcast
        resultado["rede"] = "não há"
        resultado["broadcast"] = "não há"
        resultado["hosts"] = 1
        resultado["faixa"] = inteiro_para_ip(ip)
    elif prefixo == 31:
        # Ponto a ponto (RFC 3021): os 2 endereços são hosts, sem rede/broadcast
        resultado["rede"] = "não há"
        resultado["broadcast"] = "não há"
        resultado["hosts"] = 2
        resultado["faixa"] = f"{inteiro_para_ip(rede)} a {inteiro_para_ip(broadcast)}"
    else:
        # Caso normal: 2^bits_de_host endereços, menos rede e broadcast
        resultado["rede"] = inteiro_para_ip(rede)
        resultado["broadcast"] = inteiro_para_ip(broadcast)
        resultado["hosts"] = (1 << bits_de_host) - 2
        resultado["faixa"] = f"{inteiro_para_ip(rede + 1)} a {inteiro_para_ip(broadcast - 1)}"

    return resultado


# ---------------------------------------------------------------------------
# Interface (Streamlit)
# ---------------------------------------------------------------------------

st.title("Calculadora de sub-redes IPv4")

# Campos de entrada
ip = st.text_input("Endereço IPv4", placeholder="172.16.45.200")
mascara = st.text_input("Máscara de rede", placeholder="/20 ou 255.255.240.0")

if st.button("Calcular"):
    try:
        r = calcular(ip, mascara)

        st.subheader("Resultado")
        st.write(f"**Endereço IP (binário):** {r['ip_binario']}")
        st.write(f"**Máscara (prefixo):** {r['prefixo']}")
        st.write(f"**Máscara (decimal):** {r['mascara_decimal']}")
        st.write(f"**Máscara (binário):** {r['mascara_binario']}")
        st.write(f"**Endereço da rede:** {r['rede']}")
        st.write(f"**Endereço de broadcast:** {r['broadcast']}")
        st.write(f"**Quantidade de hosts:** {r['hosts']}")
        st.write(f"**Faixa de hosts:** {r['faixa']}")
    except ValueError as erro:
        # entrada inválida mostra a mensagem de erro e a aplicação continua rodando
        st.error(str(erro))