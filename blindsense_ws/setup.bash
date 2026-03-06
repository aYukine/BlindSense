script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/install/setup.bash"

# Bash completion for launch.sh
_launch_sh_completions()
{
	local cur opts
	COMPREPLY=()
	cur="${COMP_WORDS[COMP_CWORD]}"
	opts="full client server"
	if [[ ${COMP_CWORD} == 1 ]] ; then
		COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
		return 0
	fi
}
complete -F _launch_sh_completions launch.sh ./launch.sh

# Bash completion for colcon_one.sh (package names from src/)
_colcon_one_sh_completions()
{
	local cur opts
	COMPREPLY=()
	cur="${COMP_WORDS[COMP_CWORD]}"
	opts=$(ls -1 "$script_dir/src" 2>/dev/null | grep -v '^\.' | tr '\n' ' ')
	if [[ ${COMP_CWORD} == 1 ]] ; then
		COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
		return 0
	fi
}
complete -F _colcon_one_sh_completions colcon_one.sh ./colcon_one.sh