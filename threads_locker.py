import time
import threading
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor


# Contador compartilhado por todas as threads e a trava (locker) que o protege
total = Counter()
locker = threading.Lock()


def medir_tempo_execucao(func):
    def wrapper(*args, **kwargs):
        inicio = time.perf_counter()
        resultado = func(*args, **kwargs)
        fim = time.perf_counter()
        print(f"Tempo de execução ({func.__name__}): {fim - inicio:.4f} segundos")
        return resultado

    return wrapper


def nivel_da_linha(linha):
    if "ERROR" in linha:
        return "ERROR"
    elif "WARNING" in linha:
        return "WARNING"
    elif "INFO" in linha:
        return "INFO"
    return None


def contar_sem_locker(caminho_do_arquivo):
    # Cada linha atualiza direto o contador compartilhado, SEM proteção.
    # Ler o valor e gravar o novo valor são dois passos separados: se outra
    # thread gravar no meio deles, uma das somas se perde (condição de corrida).
    with open(caminho_do_arquivo, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            nivel = nivel_da_linha(linha)
            if nivel:
                valor_atual = total[nivel]
                total[nivel] = valor_atual + 1


def contar_com_locker(caminho_do_arquivo):
    # Conta o arquivo numa variável local (só desta thread, sem disputa)...
    contagem = Counter()

    with open(caminho_do_arquivo, "r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            nivel = nivel_da_linha(linha)
            if nivel:
                contagem[nivel] += 1

    # ...e só entra na seção crítica para somar no total compartilhado.
    # Enquanto uma thread está aqui dentro, as outras esperam a vez.
    with locker:
        total.update(contagem)


@medir_tempo_execucao
def processar_logs_sem_locker(pasta="dados", max_workers=None):
    arquivos = sorted(Path(pasta).glob("*.log"))
    print(f"Processando {len(arquivos)} arquivos...")

    total.clear()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(contar_sem_locker, arquivos))

    return Counter(total)


@medir_tempo_execucao
def processar_logs_com_locker(pasta="dados", max_workers=None):
    arquivos = sorted(Path(pasta).glob("*.log"))
    print(f"Processando {len(arquivos)} arquivos...")

    total.clear()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(contar_com_locker, arquivos))

    return Counter(total)


def imprimir_resultado(titulo, resultado):
    print(titulo)
    print(f"Total de arquivos: {len(list(Path('dados').glob('*.log')))}")
    print(f"INFO:    {resultado['INFO']:>7}")
    print(f"WARNING: {resultado['WARNING']:>7}")
    print(f"ERROR:   {resultado['ERROR']:>7}")
    print()


def main():
    sem_locker = processar_logs_sem_locker(max_workers=8)
    imprimir_resultado("Resultado com threads SEM locker:", sem_locker)

    com_locker = processar_logs_com_locker(max_workers=8)
    imprimir_resultado("Resultado com threads COM locker:", com_locker)

    if sem_locker == com_locker:
        print("Os dois resultados bateram desta vez (a condição de corrida não ocorreu nesta execução).")
    else:
        perdidas = sum(com_locker.values()) - sum(sem_locker.values())
        print(f"Sem o locker, {perdidas} contagens foram perdidas por condição de corrida!")


if __name__ == "__main__":
    main()
