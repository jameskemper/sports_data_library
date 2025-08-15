      - name: Compile team stats into CSV
        working-directory: NCAA_football/team_stats_app
        run: |
          shopt -s nullglob
          files=(data/weeks_${{ env.YEAR }}/*.csv)
          usable=0
          for f in "${files[@]}"; do
            if [ -s "$f" ]; then
              usable=1
              break
            fi
          done
          if [ "$usable" -eq 1 ]; then
            python compile_team_stats.py
          else
            echo "No non-empty weekly CSVs found; skipping compile."
          fi
